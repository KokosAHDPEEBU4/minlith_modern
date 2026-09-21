"""Мини-интерпретатор Excel-формул (подмножество, реально используемое MINLITH).

Поддерживает (по аудиту 931 формулы):
  - арифметику: + - * / ( ) унарный минус
  - сравнения:  <= >= < > = <>  (внутри IF/AND/OR)
  - функции:    ROUND(x,n), IF(cond,a,b), AND(a,b,...), OR(a,b,...),
                SUM(a,b,...), COUNTA(a,b,...), TRUE, FALSE
  - ссылки:     A1-стиль (абсолютные $A$1), именованные диапазоны
  - числа с плавающей точкой (Excel: точка)

Семантика ROUND — как в Excel (half-away-from-zero), НЕ как Python round.

Использование:
    ev = ExcelEvaluator(resolver)
    val = ev.eval_formula("=ROUND(B2*10000/C2,0)", ctx_cell="D2")

resolver — объект с методом resolve(coord_or_name, sheet) -> float|bool|str|None,
возвращающий значение ячейки или именованного диапазона.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# ---------------------------------------------------------------------------
# ROUND как в Excel: half away from zero
# ---------------------------------------------------------------------------

def xround(value: float, ndigits: int = 0) -> float:
    """Excel ROUND: округление половины от нуля с учётом десятичного вида.

    Excel округляет не «сырой» double, а значение с ~15 значащими цифрами
    (из-за чего ROUND(0.145,2)=0.15, а наивный round-half-up по double дал бы
    0.14). Поэтому используем Decimal(repr(value)) — кратчайшее десятичное
    представление, восстанавливающее double.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        value = 1.0 if value else 0.0
    f = float(value)
    if f != f or f in (float("inf"), float("-inf")):
        return f
    d = Decimal(repr(f))
    q = Decimal(1).scaleb(-int(ndigits))
    return float(d.quantize(q, rounding=ROUND_HALF_UP))


def identity_round(value: float, ndigits: int = 0) -> float:
    """«Чистый» режим: ROUND не округляет (полная точность float64)."""
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return float(value)


# ---------------------------------------------------------------------------
# Токенизация
# ---------------------------------------------------------------------------

# Число: 123, 1.5, .5, 1e3? (Excel допускает E-нотацию; в MINLITH не встречается,
# но поддержим на всякий случай)
_NUM_RE = re.compile(r"(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")
# Ссылка A1 (возможно с $). НЕ fullmatch — используется match() по позиции.
_REF_A1_RE = re.compile(r"(\$?)([A-Za-z]{1,3})(\$?)(\d+)")

# Известные функции (регистронезависимо)
_FUNCS = {"ROUND", "IF", "AND", "OR", "SUM", "COUNTA"}


class FormulaError(ValueError):
    """Ошибка разбора/вычисления формулы."""


@dataclass
class Token:
    kind: str  # num | ident | op | func | lparen | rparen | comma | lt | gt | eq | ne | le | ge
    value: object


_OP2 = {"<=": "le", ">=": "ge", "<>": "ne"}
_OP1 = {"<": "lt", ">": "gt", "+": "plus", "-": "minus", "*": "star", "/": "slash", "=": "eq"}


def _tokenize(s: str) -> list[Token]:
    toks: list[Token] = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch in " \t":
            i += 1
            continue
        # двухсимвольные операторы
        two = s[i:i + 2]
        if two in _OP2:
            toks.append(Token(_OP2[two], two))
            i += 2
            continue
        if ch in _OP1:
            toks.append(Token(_OP1[ch], ch))
            i += 1
            continue
        if ch == "(":
            toks.append(Token("lparen", ch))
            i += 1
            continue
        if ch == ")":
            toks.append(Token("rparen", ch))
            i += 1
            continue
        if ch == ",":
            toks.append(Token("comma", ch))
            i += 1
            continue
        # число
        m = _NUM_RE.match(s, i)
        if m:
            txt = m.group(0)
            toks.append(Token("num", float(txt)))
            i = m.end()
            continue
        # идентификатор / функция / ссылка A1 / имя (с учётом $ для абсолютных)
        m = _IDENT_RE.match(s, i)
        if m:
            txt = m.group(0)
            up = txt.upper()
            j = m.end()
            # абсолютная ссылка вида $A$1 или $A1 или A$1: '$' перед ident
            dollar_prefix = i > 0 and s[i - 1] == "$"
            # если '$' был уже обработан отдельно - мы в ident без него
            if not dollar_prefix and j < n and s[j] == "$":
                # A$1: ident 'A' + '$' + digits - расширим
                k = j + 1
                while k < n and s[k].isdigit():
                    k += 1
                if k > j + 1:
                    txt = txt + "$" + s[j + 1:k]
                    j = k
            if j < n and s[j] == "(" and up in _FUNCS:
                toks.append(Token("func", up))
            else:
                toks.append(Token("ident", txt))
            i = j
            continue
        if ch == "$":
            # абсолютная ссылка: $A1 или $A$1
            m = _REF_A1_RE.match(s, i)
            if m:
                toks.append(Token("ident", m.group(0)))
                i = m.end()
                continue
            raise FormulaError(f"Неожиданный символ '$' на позиции {i} в: {s}")
        if ch == ":":
            toks.append(Token("colon", ch))
            i += 1
            continue
        raise FormulaError(f"Неожиданный символ {ch!r} на позиции {i} в: {s}")
    toks.append(Token("eof", ""))
    return toks


# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------

@dataclass
class NumNode:
    value: float


@dataclass
class RefNode:
    """Ссылка на ячейку A1 или именованный диапазон."""
    name: str          # как написано в формуле (без $)
    absolute: bool


@dataclass
class RangeNode:
    """Диапазон вида A1:B2 (для SUM/COUNTA)."""
    start: RefNode
    end: RefNode


@dataclass
class FuncNode:
    name: str
    args: list


@dataclass
class BinOpNode:
    op: str            # plus minus star slash lt gt le ge eq ne
    left: object
    right: object


@dataclass
class NegNode:
    operand: object


# ---------------------------------------------------------------------------
# Парсер (recursive descent)
# ---------------------------------------------------------------------------

class _Parser:
    def __init__(self, toks: list[Token]):
        self.toks = toks
        self.pos = 0

    def peek(self) -> Token:
        return self.toks[self.pos]

    def next(self) -> Token:
        t = self.toks[self.pos]
        self.pos += 1
        return t

    def expect(self, kind: str) -> Token:
        t = self.next()
        if t.kind != kind:
            raise FormulaError(f"Ожидался {kind}, получен {t.kind} ({t.value})")
        return t

    def parse(self):
        node = self.parse_or()
        self.expect("eof")
        return node

    # OR - самый низкий приоритет
    def parse_or(self):
        node = self.parse_and()
        while self.peek().kind == "ident" and str(self.peek().value).upper() == "OR":
            # OR реализован как функция, но в MINLITH OR(...) - функция. Не бинарный.
            break
        return node

    def parse_and(self):
        node = self.parse_cmp()
        return node

    def parse_cmp(self):
        node = self.parse_add()
        while self.peek().kind in ("lt", "gt", "le", "ge", "eq", "ne"):
            op = self.next()
            right = self.parse_add()
            node = BinOpNode(op.kind, node, right)
        return node

    def parse_add(self):
        node = self.parse_mul()
        while self.peek().kind in ("plus", "minus"):
            op = self.next()
            right = self.parse_mul()
            node = BinOpNode(op.kind, node, right)
        return node

    def parse_mul(self):
        node = self.parse_unary()
        while self.peek().kind in ("star", "slash"):
            op = self.next()
            right = self.parse_unary()
            node = BinOpNode(op.kind, node, right)
        return node

    def parse_unary(self):
        if self.peek().kind == "minus":
            self.next()
            return NegNode(self.parse_unary())
        return self.parse_primary()

    def parse_primary(self):
        t = self.peek()
        if t.kind == "num":
            self.next()
            return NumNode(t.value)
        if t.kind == "func":
            self.next()
            self.expect("lparen")
            args = []
            if self.peek().kind != "rparen":
                args.append(self.parse_or())
                while self.peek().kind == "comma":
                    self.next()
                    args.append(self.parse_or())
            self.expect("rparen")
            return FuncNode(t.value, args)
        if t.kind == "ident":
            self.next()
            # TRUE / FALSE
            up = str(t.value).upper()
            if up == "TRUE":
                return NumNode(1.0)
            if up == "FALSE":
                return NumNode(0.0)
            # ссылка A1 или имя
            m = _REF_A1_RE.match(t.value)
            if m and m.group(2).upper() != "R" and m.end() == len(t.value):
                # вся строка токена — это ссылка A1
                node: object = RefNode(t.value.replace("$", ""), bool(m.group(1) or m.group(3)))
            else:
                node = RefNode(t.value, False)
            # диапазон: Ref : Ref
            if self.peek().kind == "colon":
                self.next()
                end = self.parse_primary()
                if not isinstance(end, RefNode):
                    raise FormulaError("Диапазон требует Ref : Ref")
                return RangeNode(node, end)
            return node
        if t.kind == "lparen":
            self.next()
            node = self.parse_or()
            self.expect("rparen")
            return node
        raise FormulaError(f"Неожиданный токен {t.kind}({t.value})")


# ---------------------------------------------------------------------------
# Оценщик
# ---------------------------------------------------------------------------

class FormulaEvaluator:
    """Вычисляет AST формул.

    resolver: объект с методом resolve(ref: str, abs_row: bool) -> value.
    round_fn: функция округления ROUND. По умолчанию — Excel-семантика
    (xround). Для «чистого» режима без округлений передайте ``identity_round``.
    """

    def __init__(self, resolver, round_fn=None):
        self.resolver = resolver
        self.round_fn = round_fn or xround

    def eval_formula(self, formula: str) -> object:
        body = formula.strip()
        if body.startswith("="):
            body = body[1:]
        toks = _tokenize(body)
        ast = _Parser(toks).parse()
        return self.eval_node(ast)

    def eval_node(self, node) -> object:
        if isinstance(node, NumNode):
            return node.value
        if isinstance(node, NegNode):
            return -self._num(self.eval_node(node.operand))
        if isinstance(node, RefNode):
            return self.resolver.resolve(node.name)
        if isinstance(node, RangeNode):
            return self.resolver.resolve_range(node.start.name, node.end.name)
        if isinstance(node, BinOpNode):
            return self._binop(node)
        if isinstance(node, FuncNode):
            return self._func(node)
        raise FormulaError(f"Неизвестный узел {node!r}")

    def _num(self, v) -> float:
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        if v is None:
            return 0.0
        return float(v)

    def _truthy(self, v) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return v != 0.0
        return bool(v)

    def _binop(self, node: BinOpNode) -> object:
        left = self.eval_node(node.left)
        right = self.eval_node(node.right)
        op = node.op
        if op == "plus":
            return self._num(left) + self._num(right)
        if op == "minus":
            return self._num(left) - self._num(right)
        if op == "star":
            return self._num(left) * self._num(right)
        if op == "slash":
            den = self._num(right)
            if den == 0:
                # Excel: деление на 0 -> #DIV/0!. В MINLITH встречается как текст
                # (формулы не исполняются); вернём None.
                return None
            return self._num(left) / den
        # сравнения
        lv = self._num(left)
        rv = self._num(right)
        if op == "lt":
            return lv < rv
        if op == "gt":
            return lv > rv
        if op == "le":
            return lv <= rv
        if op == "ge":
            return lv >= rv
        if op == "eq":
            return lv == rv
        if op == "ne":
            return lv != rv
        raise FormulaError(f"Неизвестная операция {op}")

    def _func(self, node: FuncNode) -> object:
        name = node.name
        args = node.args
        if name == "ROUND":
            if len(args) != 2:
                raise FormulaError("ROUND требует 2 аргумента")
            x = self._num(self.eval_node(args[0]))
            n = int(self._num(self.eval_node(args[1])))
            return self.round_fn(x, n)
        if name == "SUM":
            total = 0.0
            for a in args:
                v = self.eval_node(a)
                if isinstance(v, (list, tuple)):
                    total += sum(self._num(x) for x in v if x is not None)
                elif v is not None:
                    total += self._num(v)
            return total
        if name == "COUNTA":
            cnt = 0.0
            for a in args:
                v = self.eval_node(a)
                if isinstance(v, (list, tuple)):
                    cnt += sum(1.0 for x in v if x is not None and x != "")
                elif v is not None and v != "":
                    cnt += 1.0
            return cnt
        if name == "AND":
            return all(self._truthy(self.eval_node(a)) for a in args)
        if name == "OR":
            return any(self._truthy(self.eval_node(a)) for a in args)
        if name == "IF":
            if len(args) == 2:
                return self.eval_node(args[1]) if self._truthy(self.eval_node(args[0])) else 0.0
            if len(args) >= 3:
                return (self.eval_node(args[1]) if self._truthy(self.eval_node(args[0]))
                        else self.eval_node(args[2]))
            raise FormulaError("IF требует 2-3 аргумента")
        raise FormulaError(f"Неизвестная функция {name}")
