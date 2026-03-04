"""
Enrich Stride Data with GTFS Routes

This module provides a QGIS processing algorithm for enriching vehicle location
data with GTFS route information from the Open Bus Stride API.
"""

from qgis.core import (
    NULL,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterField,
    QgsProcessingParameterVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication, QVariant

from ...requests.stride_api_client import StrideAPIClient


class EnrichWithRoutes(QgsProcessingAlgorithm):
    """
    Enriches a point layer with GTFS route information from the Stride API.

    Takes a layer with line_ref values, queries the GTFS routes API for each
    unique line reference, and joins the route data back to the features.
    """

    # Parameter names
    INPUT_LAYER = "INPUT_LAYER"
    LINE_REF_FIELD = "LINE_REF_FIELD"
    OUTPUT = "OUTPUT"

    # Additional fields from GTFS routes API
    ROUTE_FIELDS = [
        # ('id', QVariant.Int),
        ("date", QVariant.String),
        ("siri_line_ref", QVariant.Int),
        ("siri_operator_ref", QVariant.Int),
        ("route_short_name", QVariant.String),
        ("route_long_name", QVariant.String),
        ("route_mkt", QVariant.String),
        ("route_direction", QVariant.String),
        ("route_alternative", QVariant.String),
        ("route_desc", QVariant.String),
        ("agency_name", QVariant.String),
        ("route_type", QVariant.String),
    ]

    # Mapping from output field names to API response field names
    GTFS_FIELD_MAP = {
        "siri_line_ref": "line_ref",
        "siri_operator_ref": "operator_ref",
    }

    def tr(self, string):
        """Translate strings for internationalization."""
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        """Create a new instance of the algorithm."""
        return EnrichWithRoutes()

    def name(self):
        """Algorithm name for command-line usage."""
        return "enrichwithroutes"

    def displayName(self):
        """Human-readable algorithm name."""
        return self.tr("Enrich with GTFS Route Data")

    # def group(self):
    #     """Algorithm group name."""
    #     return self.tr('Stride')

    # def groupId(self):
    #     """Algorithm group identifier."""
    #     return 'stride'

    def shortHelpString(self):
        """Algorithm description and usage help."""
        return self.tr(
            """Enriches a layer with GTFS route information from the 
            Open Bus Stride API.
            
            Takes a layer containing line_ref values, queries the GTFS routes 
            API for each unique line reference, and joins the route data 
            (route names, descriptions, agency info, etc.) to the features.
            
            Parameters:
            - Input Layer: Layer containing line_ref field
            - Line Reference Field: Field containing line_ref values
            
            The algorithm automatically extracts the date range from the 
            recorded_at field in the input data.
            
            The output will contain all original fields plus additional GTFS 
            route information fields.
            """
        )

    def initAlgorithm(self, config=None):
        """Define the algorithm parameters."""
        self.addParameter(
            QgsProcessingParameterVectorLayer(self.INPUT_LAYER, self.tr("Input Layer"))
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.LINE_REF_FIELD,
                self.tr("Line Reference Field"),
                parentLayerParameterName=self.INPUT_LAYER,
                defaultValue="siri_line_ref",
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT, self.tr("Enriched SIRI Locations")
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """Execute the algorithm."""
        # Get input layer and field
        input_layer = self.parameterAsVectorLayer(parameters, self.INPUT_LAYER, context)
        line_ref_field = self.parameterAsString(
            parameters, self.LINE_REF_FIELD, context
        )

        if input_layer is None:
            raise QgsProcessingException(self.tr("Invalid input layer"))

        # Step 1: Extract unique line_refs and date range from data
        feedback.pushInfo(
            self.tr("Step 1/3: Extracting unique line references and date range...")
        )
        feedback.setProgress(0)

        unique_line_refs, date_from, date_to = self._extract_unique_line_refs_and_dates(
            input_layer, line_ref_field, feedback
        )

        if not unique_line_refs:
            raise QgsProcessingException(
                self.tr("No valid line references found in the input layer")
            )

        feedback.pushInfo(
            self.tr(f"Found {len(unique_line_refs)} unique line reference(s)")
        )
        feedback.pushInfo(self.tr(f"Date range: {date_from} to {date_to}"))
        feedback.setProgress(20)

        # Step 2: Fetch route data from API
        feedback.pushInfo(self.tr("Step 2/3: Fetching GTFS route data..."))

        route_data_map = self._fetch_route_data(
            unique_line_refs, date_from, date_to, feedback
        )

        feedback.setProgress(60)

        # Step 3: Create enriched output
        feedback.pushInfo(self.tr("Step 3/3: Creating enriched output..."))

        sink = self._create_output_sink(parameters, context, input_layer)
        self._enrich_features(
            input_layer, line_ref_field, route_data_map, sink, feedback
        )

        feedback.setProgress(100)
        feedback.pushInfo(self.tr("Enrichment complete!"))

        return {self.OUTPUT: sink[1]}

    def _extract_unique_line_refs_and_dates(self, layer, field_name, feedback):
        """
        Extract unique line_ref values and date range from the input layer.

        Args:
            layer: Input vector layer
            field_name (str): Name of the line_ref field
            feedback: Processing feedback object

        Returns:
            tuple: (set of unique line_refs, date_from str, date_to str)
        """
        from qgis.PyQt.QtCore import QDateTime

        field_index = layer.fields().indexFromName(field_name)
        if field_index == -1:
            raise QgsProcessingException(
                self.tr(f'Field "{field_name}" not found in input layer')
            )

        unique_refs = set()
        min_date = None
        max_date = None

        for feature in layer.getFeatures():
            if feedback.isCanceled():
                break

            # Extract line_ref
            value = feature[field_name]
            if value is not None and value != NULL:
                try:
                    unique_refs.add(int(value))
                except (ValueError, TypeError):
                    feedback.reportError(self.tr(f"Invalid line_ref value: {value}"))

            # Extract date from available date fields (try in order)
            date_fields = ["recorded_at", "begin", "end", "scheduled_start"]
            for date_field in date_fields:
                # Check if field exists in the layer
                if layer.fields().indexFromName(date_field) == -1:
                    continue

                date_value = feature.attribute(date_field)
                if date_value is not None and isinstance(date_value, QDateTime):
                    if min_date is None or date_value < min_date:
                        min_date = date_value
                    if max_date is None or date_value > max_date:
                        max_date = date_value
                    break  # Found a valid date field, stop trying others

        # Format dates as YYYY-MM-DD
        if min_date and max_date:
            date_from = min_date.toString("yyyy-MM-dd")
            date_to = max_date.toString("yyyy-MM-dd")
        else:
            # Fallback to today's date if no valid dates found
            from datetime import date

            today = date.today().isoformat()
            date_from = today
            date_to = today
            feedback.pushInfo(
                self.tr("No valid dates found in data, using today's date")
            )

        return unique_refs, date_from, date_to

    def _fetch_route_data(self, line_refs, date_from, date_to, feedback):
        """
        Fetch GTFS route data for all line references in a single request.

        Args:
            line_refs (set): Set of line_ref values to query
            date_from (str): Start date
            date_to (str): End date
            feedback: Processing feedback object

        Returns:
            dict: Map of line_ref -> route data
        """
        api_client = StrideAPIClient(feedback)
        route_data_map = {}

        # Convert line_refs to comma-separated string
        line_refs_str = ",".join(str(ref) for ref in sorted(line_refs))

        feedback.pushInfo(
            self.tr(f"Fetching route data for {len(line_refs)} line reference(s)...")
        )

        # Build query parameters with all line_refs
        params = {
            "get_count": "false",
            "date_from": date_from,
            "date_to": date_to,
            "line_refs": line_refs_str,
            "order_by": "id asc",
        }

        try:
            data = api_client.fetch_data("/gtfs_routes/list", params)

            if data and len(data) > 0:
                feedback.pushInfo(
                    self.tr(f"Received {len(data)} route record(s) from API")
                )

                # Build map from line_ref to route data
                for route in data:
                    line_ref = route.get("line_ref")
                    if line_ref is not None:
                        # Store first occurrence for each line_ref
                        if line_ref not in route_data_map:
                            route_data_map[line_ref] = route
                            feedback.pushInfo(
                                self.tr(
                                    f"  Line {line_ref}: {route.get('route_long_name', 'N/A')}"
                                )
                            )

                # Mark missing line_refs as None
                for line_ref in line_refs:
                    if line_ref not in route_data_map:
                        route_data_map[line_ref] = None
                        feedback.pushInfo(
                            self.tr(f"  Line {line_ref}: No route data found")
                        )
            else:
                feedback.pushInfo(self.tr("No route data received from API"))
                # Mark all as None
                for line_ref in line_refs:
                    route_data_map[line_ref] = None

        except Exception as e:
            feedback.reportError(self.tr(f"Error fetching route data: {str(e)}"))
            # Mark all as None on error
            for line_ref in line_refs:
                route_data_map[line_ref] = None

        return route_data_map

    def _create_output_sink(self, parameters, context, input_layer):
        """
        Create the output feature sink with enriched fields.

        Args:
            parameters: Algorithm parameters
            context: Processing context
            input_layer: Input vector layer

        Returns:
            tuple: (sink, dest_id)
        """
        # Create output fields (original + route fields)
        output_fields = QgsFields(input_layer.fields())

        for field_name, field_type in self.ROUTE_FIELDS:
            if output_fields.indexFromName(field_name) == -1:
                output_fields.append(QgsField(field_name, field_type))

        # Create sink
        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            output_fields,
            input_layer.wkbType(),
            input_layer.sourceCrs(),
        )

        if sink is None:
            raise QgsProcessingException(self.tr("Invalid output specified."))

        return (sink, dest_id)

    def _enrich_features(
        self, input_layer, line_ref_field, route_data_map, sink_info, feedback
    ):
        """
        Create enriched features with route data joined.

        Args:
            input_layer: Input vector layer
            line_ref_field (str): Name of the line_ref field
            route_data_map (dict): Map of line_ref -> route data
            sink_info (tuple): (sink, dest_id)
            feedback: Processing feedback object
        """
        sink = sink_info[0]

        # Get output field structure
        output_fields = QgsFields(input_layer.fields())

        # Track which fields are actually new (not duplicates)
        new_route_fields = []
        for field_name, field_type in self.ROUTE_FIELDS:
            if output_fields.indexFromName(field_name) == -1:
                output_fields.append(QgsField(field_name, field_type))
                new_route_fields.append(field_name)

        total = input_layer.featureCount()
        for i, in_feature in enumerate(input_layer.getFeatures()):
            if feedback.isCanceled():
                break

            # Create output feature
            out_feature = QgsFeature(output_fields)
            out_feature.setGeometry(in_feature.geometry())

            # Copy original attributes
            attributes = list(in_feature.attributes())

            # Get line_ref and look up route data
            line_ref = in_feature[line_ref_field]
            route_data = None

            if line_ref is not None and line_ref != NULL:
                try:
                    route_data = route_data_map.get(int(line_ref))
                except (ValueError, TypeError):
                    pass

            # Add route fields (only those that were actually added as new fields)
            for field_name in new_route_fields:
                if route_data:
                    # Special handling for route_desc (calculated field)
                    if field_name == "route_desc":
                        route_mkt = route_data.get("route_mkt", "")
                        route_direction = route_data.get("route_direction", "")
                        route_alternative = route_data.get("route_alternative", "")
                        value = f"{route_mkt}-{route_direction}-{route_alternative}"
                    else:
                        # Map field name to API key if needed
                        api_key = self.GTFS_FIELD_MAP.get(field_name, field_name)
                        value = route_data.get(api_key)
                    attributes.append(value if value is not None else NULL)
                else:
                    attributes.append(NULL)

            out_feature.setAttributes(attributes)
            sink.addFeature(out_feature, QgsFeatureSink.FastInsert)

            # Update progress (60-100%)
            if total > 0:
                progress = 60 + int((i + 1) / total * 40)
                feedback.setProgress(progress)
