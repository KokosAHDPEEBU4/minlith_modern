"""Tests for GeologicalTheoryAlgorithm — движок строго по теории (файлы 00-07).

Основано на разобранном числовом примере из файла 06 (состав T-O2):
SiO2=52.5, Al2O3=23.41, Fe2O3=1.71, FeO=8.06, MgO=2.35, CaO=0.28,
Na2O=0.94, K2O=3.45.
"""

from __future__ import annotations

import pytest

from src.core.calculator import Calculator
from src.core.geological_theory import GeologicalTheoryAlgorithm
from src.core.models import OxideComposition, Sample
from src.core.stage1 import stage1
from src.core.stage2 import classify_rock_type, k_or_for_type, stage2
from src.core.stage3 import stage3


def _t_o2_sample() -> Sample:
    return Sample(
        name="T-O2",
        composition=OxideComposition(
            sio2=52.5, al2o3=23.41, fe2o3=1.71, feo=8.06,
            mgo=2.35, cao=0.28, na2o=0.94, k2o=3.45,
        ),
    )


class TestStage1:
    def test_apatite_only(self):
        minerals, res = stage1({"p2o5": 10.0, "cao": 50.0, "feo": 0.0,
                                "s": 0.0, "so3": 0.0, "f": 0.0, "cl": 0.0})
        assert minerals["ap"] == pytest.approx(10.0)
        assert res["cao"] == pytest.approx(50.0 - 3.33 * 10.0)
        assert res["p2o5"] == 0.0

    def test_pyrite_consumes_feo(self):
        minerals, res = stage1({"p2o5": 0.0, "cao": 0.0, "feo": 20.0,
                                "s": 10.0, "so3": 0.0, "f": 0.0, "cl": 0.0})
        assert minerals["py"] == pytest.approx(5.0)
        assert res["feo"] == pytest.approx(15.0)

    def test_gypsum_consumes_cao(self):
        minerals, res = stage1({"p2o5": 0.0, "cao": 10.0, "feo": 0.0,
                                "s": 0.0, "so3": 4.0, "f": 0.0, "cl": 0.0})
        assert minerals["gy"] == pytest.approx(4.0)
        assert res["cao"] == pytest.approx(6.0)

    def test_fluorite_uses_f(self):
        minerals, res = stage1({"p2o5": 0.0, "cao": 10.0, "feo": 0.0,
                                "s": 0.0, "so3": 0.0, "f": 8.0, "cl": 0.0})
        assert minerals["fl"] == pytest.approx(4.0)
        assert res["cao"] == pytest.approx(6.0)

    def test_halite_consumes_na(self):
        minerals, res = stage1({"p2o5": 0.0, "cao": 0.0, "feo": 0.0,
                                "s": 0.0, "so3": 0.0, "f": 0.0, "cl": 6.0,
                                "na2o": 10.0})
        assert minerals["hl"] == pytest.approx(3.0)
        assert res["na2o"] == pytest.approx(7.0)


class TestClassification:
    def test_high_r_is_type4(self):
        """T-O2: R = Al/(Na+K+Ca) ≈ 4.04 → глина (тип 4)."""
        # моли из файла 06
        al, na, k, ca = 0.22960, 0.01517, 0.03662, 0.00499
        assert classify_rock_type(al, na, k, ca) == 4

    def test_low_r_is_type1(self):
        """Низкое R → кварцевый песчаник (тип 1)."""
        assert classify_rock_type(1.0, 2.0, 1.0, 1.0) == 1

    def test_k_or_table(self):
        assert k_or_for_type(1) == pytest.approx(1.0)
        assert k_or_for_type(2) == pytest.approx(0.7)
        assert k_or_for_type(3) == pytest.approx(0.5)
        assert k_or_for_type(4) == pytest.approx(0.2)
        assert k_or_for_type(5) == pytest.approx(0.1)


class TestStage2:
    def test_or_uses_k_or(self):
        fe = {"al2o3": 20.0, "na2o": 5.0, "k2o": 10.0, "cao": 2.0,
              "sio2": 200.0, "mgo": 0.0, "feo": 0.0}
        minerals, res = stage2(fe, rock_type=2, k_or=0.7)
        assert minerals["or"] == pytest.approx(0.7 * 10.0)
        assert res["al2o3"] == pytest.approx(
            20.0 - 7.0 - 5.0 - 2.0 - 3 * minerals["ilt"])
        assert res["sio2"] == pytest.approx(
            200.0 - 6 * 7.0 - 6 * 5.0 - 2 * 2.0 - 6 * minerals["ilt"])

    def test_illite_gets_remaining_k(self):
        fe = {"al2o3": 30.0, "na2o": 0.0, "k2o": 10.0, "cao": 0.0,
              "sio2": 300.0, "mgo": 0.0, "feo": 0.0}
        minerals, _ = stage2(fe, rock_type=4, k_or=0.2)
        assert minerals["or"] == pytest.approx(0.2 * 10.0)
        assert minerals["ilt"] == pytest.approx(0.8 * 10.0)

    def test_gibbsite_takes_remainder(self):
        """Гиббсит — «минерал последней инстанции»: Al, не ушедший в глины.

        При высоком Al и низком Si каолинит ограничен кремнезёмом,
        избыточный Al уходит в гиббсит.
        """
        fe = {"al2o3": 10.0, "na2o": 0.0, "k2o": 0.0, "cao": 0.0,
              "sio2": 8.0, "mgo": 0.0, "feo": 0.0}
        minerals, _ = stage2(fe, rock_type=5, k_or=0.1)
        assert minerals["kln"] == pytest.approx(4.0)  # Si/2 = 4
        assert minerals["gbs"] == pytest.approx(6.0)  # Al остаток


class TestStage3:
    def test_dolomite_calcite_siderite(self):
        fe = {"cao": 10.0, "mgo": 5.0, "feo": 3.0, "fe2o3": 0.0,
              "co2": 20.0, "tio2": 0.0, "mno": 0.0, "sio2": 0.0}
        minerals = {}
        stage3(fe, minerals)
        assert minerals["dl"] == pytest.approx(5.0)
        assert minerals["cc"] == pytest.approx(5.0)
        assert minerals["sd"] == pytest.approx(3.0)

    def test_rhodochrosite_from_mn(self):
        fe = {"cao": 0.0, "mgo": 0.0, "feo": 0.0, "fe2o3": 0.0,
              "co2": 0.0, "tio2": 0.0, "mno": 2.0, "sio2": 5.0}
        minerals = {}
        stage3(fe, minerals)
        assert minerals["rch"] == pytest.approx(2.0)
        assert minerals["qz"] == pytest.approx(5.0)

    def test_rutile_from_tio2(self):
        fe = {"cao": 0.0, "mgo": 0.0, "feo": 0.0, "fe2o3": 0.0,
              "co2": 0.0, "tio2": 3.0, "mno": 0.0, "sio2": 0.0}
        minerals = {}
        stage3(fe, minerals)
        assert minerals["rt"] == pytest.approx(3.0)


class TestGeologicalTheoryAlgorithm:
    def test_returns_algorithm_output(self):
        calc = Calculator(algorithm=GeologicalTheoryAlgorithm())
        result = calc.calculate_single(_t_o2_sample())
        assert result.minerals_weight is not None

    def test_worked_example_06_balance(self):
        """Пример из файла 06: баланс сходится, кварц/FeO/MgO не отрицательны."""
        calc = Calculator(algorithm=GeologicalTheoryAlgorithm())
        result = calc.calculate_single(_t_o2_sample())

        # Кварц не отрицательный
        assert result.defect["sio2"] >= 0
        # FeO не перерасходован
        assert result.defect["feo"] >= 0
        # MgO не перерасходован
        assert result.defect["mgo"] >= 0

    def test_quartz_dominant_rock(self):
        """Чистый кварц → почти весь состав в кварце."""
        calc = Calculator(algorithm=GeologicalTheoryAlgorithm())
        s = Sample(name="quartz", composition=OxideComposition(sio2=100.0))
        r = calc.calculate_single(s)
        assert r.minerals_weight.q > 90.0

    def test_albite_dominant(self):
        calc = Calculator(algorithm=GeologicalTheoryAlgorithm())
        s = Sample(name="albite", composition=OxideComposition(
            sio2=68.7, al2o3=19.5, na2o=11.8))
        r = calc.calculate_single(s)
        assert r.minerals_weight.ab > 50.0

    def test_illite_kaolinite_balance(self):
        """T-O2: после полевых шпатов K уходит в иллит, Al — в каолинит."""
        calc = Calculator(algorithm=GeologicalTheoryAlgorithm())
        result = calc.calculate_single(_t_o2_sample())
        assert result.minerals_weight.ill > 0
        assert result.minerals_weight.kn > 0

    def test_sum_normalized(self):
        calc = Calculator(algorithm=GeologicalTheoryAlgorithm())
        result = calc.calculate_single(_t_o2_sample())
        total = sum(v for k, v in result.minerals_weight.__dict__.items()
                    if not k.startswith("_"))
        assert 99.0 <= total <= 101.0
