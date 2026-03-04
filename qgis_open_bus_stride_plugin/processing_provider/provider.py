from pathlib import Path

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from .algorithms.enrich_with_routes import EnrichWithRoutes
from .algorithms.get_locations import GetLocations
from .algorithms.route_speed_from_locations import RouteSpeedFromLocations


class StridePluginProcessingProvider(QgsProcessingProvider):
    """The provider of our plugin."""

    def loadAlgorithms(self):
        """Load each algorithm into the current provider."""
        self.addAlgorithm(GetLocations())
        self.addAlgorithm(EnrichWithRoutes())
        self.addAlgorithm(RouteSpeedFromLocations())

    def id(self) -> str:
        """The ID of your plugin, used for identifying the provider.

        This string should be a unique, short, character only string,
        eg "qgis" or "gdal". This string should not be localised.
        """
        return "openbusstride"

    def name(self) -> str:
        """The human friendly name of your plugin in Processing.

        This string should be as short as possible (e.g. "Lastools", not
        "Lastools version 1.0.1 64-bit") and localised.
        """
        return self.tr("Open Bus Stride Plugin")

    def icon(self) -> QIcon:
        """Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        icon_path = str((Path(__file__).parent / ".." / "icon.svg").resolve())
        return QIcon(icon_path)
