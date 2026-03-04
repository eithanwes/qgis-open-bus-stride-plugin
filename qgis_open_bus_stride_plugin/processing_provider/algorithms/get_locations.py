"""
Get Stride Data Duration Algorithm

This module provides a QGIS processing algorithm for fetching vehicle location
data from the Open Bus Stride API using time-based queries.
"""

from qgis.core import (
    NULL,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterDateTime,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QCoreApplication, QDateTime, Qt, QVariant

from ...requests.stride_api_client import StrideAPIClient


class GetLocations(QgsProcessingAlgorithm):
    """
    Fetches data from the Open Bus Stride API using a start time and duration,
    and saves it as a typed layer in the Israel Grid (EPSG:2039) CRS.
    """

    # Parameter names
    INPUT_PATH = "INPUT_PATH"
    INPUT_PARAMS = "INPUT_PARAMS"
    INPUT_EXTENT = "INPUT_EXTENT"
    INPUT_START_TIME = "INPUT_START_TIME"
    INPUT_DURATION = "INPUT_DURATION"
    OUTPUT = "OUTPUT"

    # Field mapping from API response to output layer
    FIELD_DEFINITIONS = [
        ("id", QVariant.LongLong),
        ("snapshot_id", QVariant.LongLong),
        ("ride_stop_id", QVariant.LongLong),
        ("recorded_at", QVariant.DateTime),
        ("lon", QVariant.Double),
        ("lat", QVariant.Double),
        ("bearing", QVariant.Int),
        ("velocity", QVariant.Int),
        ("dist_from_start", QVariant.Int),
        ("dist_from_stop", QVariant.Double),
        ("siri_route_id", QVariant.Int),
        ("siri_line_ref", QVariant.Int),
        ("siri_operator_ref", QVariant.Int),
        ("siri_ride_id", QVariant.LongLong),
        ("journey_ref", QVariant.String),
        ("scheduled_start", QVariant.DateTime),
        ("vehicle_ref", QVariant.String),
    ]

    KEY_MAP = {
        "siri_snapshot_id": "snapshot_id",
        "siri_ride_stop_id": "ride_stop_id",
        "recorded_at_time": "recorded_at",
        "distance_from_journey_start": "dist_from_start",
        "distance_from_siri_ride_stop_meters": "dist_from_stop",
        "siri_snapshot__snapshot_id": "snapshot_id",
        "siri_route__id": "siri_route_id",
        "siri_route__line_ref": "siri_line_ref",
        "siri_route__operator_ref": "siri_operator_ref",
        "siri_ride__id": "siri_ride_id",
        "siri_ride__journey_ref": "journey_ref",
        "siri_ride__scheduled_start_time": "scheduled_start",
        "siri_ride__vehicle_ref": "vehicle_ref",
    }

    def tr(self, string):
        """Translate strings for internationalization."""
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        """Create a new instance of the algorithm."""
        return GetLocations()

    def name(self):
        """Algorithm name for command-line usage."""
        return "getlocations"

    def displayName(self):
        """Human-readable algorithm name."""
        return self.tr("Get Open Bus Stride Data (Duration-based)")

    # def group(self):
    #     """Algorithm group name."""
    #     return self.tr('Stride')

    # def groupId(self):
    #     """Algorithm group identifier."""
    #     return 'stride'

    def shortHelpString(self):
        """Algorithm description and usage help."""
        return self.tr(
            """Fetches vehicle location data from the Open Bus Stride API using 
            a start time and duration in minutes.
            
            The output layer will be in the Israel Grid (EPSG:2039) CRS.
            
            Parameters:
            - API Path: The endpoint to query (default: /siri_vehicle_locations/list)
            - Filter by Extent: Optional spatial filter
            - Start Time: Beginning of the time window (UTC)
            - Duration: Length of time window in minutes
            - Additional Parameters: Optional query parameters as Python dictionary
            """
        )

    def initAlgorithm(self, config=None):
        """Define the algorithm parameters."""
        self.addParameter(
            QgsProcessingParameterString(
                self.INPUT_PATH,
                self.tr("API Path"),
                defaultValue="/siri_vehicle_locations/list",
            )
        )

        self.addParameter(
            QgsProcessingParameterExtent(
                self.INPUT_EXTENT, self.tr("Filter by Extent"), optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterDateTime(
                self.INPUT_START_TIME, self.tr("Start Time (UTC)"), optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.INPUT_DURATION,
                self.tr("Duration (minutes)"),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=5,
                minValue=1,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.INPUT_PARAMS,
                self.tr("Additional Request Parameters (as Python dictionary)"),
                optional=True,
                defaultValue="{'limit': 1000}",
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT, self.tr("Output SIRI Locations")
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """Execute the algorithm."""
        # Extract parameters
        api_path = self.parameterAsString(parameters, self.INPUT_PATH, context)
        params_str = self.parameterAsString(parameters, self.INPUT_PARAMS, context)
        extent = self.parameterAsExtent(parameters, self.INPUT_EXTENT, context)
        extent_crs = self.parameterAsExtentCrs(parameters, self.INPUT_EXTENT, context)
        start_time = self.parameterAsDateTime(
            parameters, self.INPUT_START_TIME, context
        )
        duration_minutes = self.parameterAsInt(parameters, self.INPUT_DURATION, context)

        # Parse additional parameters
        params = self._parse_parameters(params_str)

        # Add spatial filter if extent provided
        if not extent.isNull():
            self._add_spatial_filter(params, extent, extent_crs, context)

        # Add temporal filter if start time provided
        if start_time.isValid():
            self._add_temporal_filter(params, start_time, duration_minutes)

        # Phase 1: Download data
        feedback.pushInfo(self.tr("Phase 1/2: Downloading data..."))
        feedback.setProgress(0)

        api_client = StrideAPIClient(feedback)
        data = api_client.fetch_data(api_path, params)

        if not data:
            feedback.pushInfo(self.tr("No data received from API."))
            return {self.OUTPUT: None}

        feedback.setProgress(50)

        # Phase 2: Process features
        feedback.pushInfo(self.tr("Phase 2/2: Processing features..."))
        sink = self._create_output_sink(parameters, context)

        self._process_features(data, sink, context, feedback)

        feedback.setProgress(100)
        return {self.OUTPUT: sink[1]}

    def _parse_parameters(self, params_str):
        """
        Parse the additional parameters string into a dictionary.

        Args:
            params_str (str): String representation of parameters dictionary

        Returns:
            dict: Parsed parameters

        Raises:
            QgsProcessingException: If parameters cannot be parsed
        """
        params = {}
        if params_str:
            try:
                params = eval(params_str)
                if not isinstance(params, dict):
                    raise TypeError("Parameters must be a dictionary")
            except (SyntaxError, TypeError) as e:
                raise QgsProcessingException(
                    self.tr(f"Invalid format for parameters: {e}")
                )
        return params

    def _add_spatial_filter(self, params, extent, extent_crs, context):
        """
        Add spatial bounding box filter to parameters.

        Args:
            params (dict): Parameters dictionary to update
            extent: QgsRectangle extent
            extent_crs: Source CRS of the extent
            context: Processing context
        """
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(
            extent_crs, target_crs, context.transformContext()
        )
        extent_wgs84 = transform.transform(extent)

        params["lon__greater_or_equal"] = extent_wgs84.xMinimum()
        params["lon__lower_or_equal"] = extent_wgs84.xMaximum()
        params["lat__greater_or_equal"] = extent_wgs84.yMinimum()
        params["lat__lower_or_equal"] = extent_wgs84.yMaximum()

    def _add_temporal_filter(self, params, start_time, duration_minutes):
        """
        Add temporal filter to parameters.

        Args:
            params (dict): Parameters dictionary to update
            start_time (QDateTime): Start of time window
            duration_minutes (int): Duration in minutes
        """
        iso_format = "yyyy-MM-ddTHH:mm:ss.zzz'Z'"
        params["recorded_at_time_from"] = start_time.toString(iso_format)

        if duration_minutes > 0:
            end_time = start_time.addSecs(duration_minutes * 60)
            params["recorded_at_time_to"] = end_time.toString(iso_format)

    def _create_output_sink(self, parameters, context):
        """
        Create the output feature sink with proper fields and CRS.

        Args:
            parameters: Algorithm parameters
            context: Processing context

        Returns:
            tuple: (sink, dest_id)

        Raises:
            QgsProcessingException: If sink creation fails
        """
        # Create output fields
        fields = QgsFields()
        for field_name, field_type in self.FIELD_DEFINITIONS:
            fields.append(QgsField(field_name, field_type))

        # Use Israel Grid CRS
        dest_crs = QgsCoordinateReferenceSystem("EPSG:2039")

        # Create sink
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context, fields, QgsWkbTypes.Point, dest_crs
        )

        if sink is None:
            raise QgsProcessingException(self.tr("Invalid output specified."))

        return (sink, dest_id)

    def _process_features(self, data, sink_info, context, feedback):
        """
        Process API data and add features to the output sink.

        Args:
            data (list): List of data items from API
            sink_info (tuple): (sink, dest_id) from _create_output_sink
            context: Processing context
            feedback: Processing feedback object
        """
        sink = sink_info[0]
        total = len(data)
        feedback.pushInfo(self.tr(f"Processing {total} features..."))

        # Setup coordinate transformation
        source_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        dest_crs = QgsCoordinateReferenceSystem("EPSG:2039")
        transform = QgsCoordinateTransform(
            source_crs, dest_crs, context.transformContext()
        )

        # Process each feature
        for i, item in enumerate(data):
            if feedback.isCanceled():
                break

            feature = self._create_feature(item, transform)
            if feature is not None:
                sink.addFeature(feature, QgsFeatureSink.FastInsert)

            # Update progress (50-100%)
            progress = 50 + int((i + 1) / total * 50)
            feedback.setProgress(progress)

    def _create_feature(self, item, transform):
        """
        Create a feature from an API data item.

        Args:
            item (dict): Single data item from API response
            transform: QgsCoordinateTransform for geometry transformation

        Returns:
            QgsFeature or None: Created feature, or None if invalid
        """
        # Create fields
        fields = QgsFields()
        for field_name, field_type in self.FIELD_DEFINITIONS:
            fields.append(QgsField(field_name, field_type))

        feature = QgsFeature(fields)

        # Set geometry
        if item.get("lon") is not None and item.get("lat") is not None:
            try:
                point_wgs84 = QgsPointXY(float(item["lon"]), float(item["lat"]))
                geom = QgsGeometry.fromPointXY(transform.transform(point_wgs84))
                feature.setGeometry(geom)
            except (ValueError, TypeError):
                return None
        else:
            return None

        # Set attributes
        attributes = []
        for field in fields:
            original_key = next(
                (k for k, v in self.KEY_MAP.items() if v == field.name()), field.name()
            )
            val = item.get(original_key)

            if val is None:
                attributes.append(NULL)
            elif field.type() == QVariant.DateTime:
                dt = QDateTime.fromString(val, Qt.DateFormat.ISODate)
                attributes.append(dt)
            else:
                attributes.append(val)

        feature.setAttributes(attributes)
        return feature
