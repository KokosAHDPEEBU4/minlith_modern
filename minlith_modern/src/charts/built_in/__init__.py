"""Built-in chart plugins."""

from src.charts.built_in.bar_chart import BarChart
from src.charts.built_in.pie_chart import PieChart
from src.charts.built_in.defect_chart import DefectChart
from src.charts.built_in.qapf import QAPFChart
from src.charts.built_in.tas import TASChart
from src.charts.built_in.acnk import ACNKChart
from src.charts.built_in.heatmap import HeatmapChart
from src.charts.built_in.rock_type_chart import RockTypeChart
from src.charts.built_in.feldspar_triangle import FeldsparTriangle
from src.charts.built_in.harker import HarkerPlugin
from src.charts.built_in.afm import AFMPlugin
from src.charts.built_in.sio2_k2o import SiO2K2OPlugin
from src.charts.built_in.bland_altman import BlandAltmanPlugin
from src.charts.built_in.correlation import CorrelationPlugin

BUILTIN_CHARTS: list = [
    BarChart(),
    PieChart(),
    DefectChart(),
    QAPFChart(),
    TASChart(),
    ACNKChart(),
    HeatmapChart(),
    RockTypeChart(),
    FeldsparTriangle(),
    HarkerPlugin(),
    AFMPlugin(),
    SiO2K2OPlugin(),
    BlandAltmanPlugin(),
    CorrelationPlugin(),
]
