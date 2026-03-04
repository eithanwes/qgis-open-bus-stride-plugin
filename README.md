# QGIS Open Bus Stride Plugin

A powerful QGIS plugin that integrates with the [Open Bus Stride API](https://open-bus-map-search.hasadna.org.il/) to fetch, enrich, and analyze public transportation vehicle location data directly within QGIS.

## About Open Bus Stride

The Public Knowledge Workshop's Stride project provides usable and accurate data about the Israeli public transportation system.

Learn more: [Open Bus Stride Documentation](https://open-bus-stride-api.hasadna.org.il/docs)

## Features

This plugin provides processing algorithms integrated into QGIS:

### 1. Get Locations
Fetch vehicle location data from the Open Bus Stride API using time-based queries. Returns GPS points with detailed attributes including:
- Location (longitude, latitude)
- Timestamp
- Velocity and bearing
- Route and operator information
- Distance from route start/stop

### 2. Enrich with Routes
Enrich existing location point data with additional route attributes by joining location points to GTFS route shapes based on route IDs.


## Installation

1. Download the plugin from the [releases page](https://github.com/eithanwes/qgis-open-bus-stride-plugin/releases)
2. Open QGIS and enable the plugin via **Plugins > Manage and Install Plugins > install from ZIP** 
3. Once installed, access the processing algorithms via the Processing Toolbox

## Usage

Once installed, the plugin appears as a processing provider in QGIS. Access the algorithms via:
- **Processing Toolbox** → Search for "Open Bus Stride"
- Or use them in Processing Models and Scripts

### Typical Workflow

1. **Get Locations**: Query the Stride API for vehicle locations within a time range and geographic extent
2. **Enrich with Routes**: Optionally join location data with GTFS route geometries
3. **Analyze Speed**: Create route segments and calculate speed metrics for analysis



### Example: Location Data Visualization
<img width="500" height="426" alt="Image" src="https://private-user-images.githubusercontent.com/209318276/558223299-da0fd91f-b8a8-4e12-bedc-2a2c70b6b654.png?jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3NzI2NDY1NjAsIm5iZiI6MTc3MjY0NjI2MCwicGF0aCI6Ii8yMDkzMTgyNzYvNTU4MjIzMjk5LWRhMGZkOTFmLWI4YTgtNGUxMi1iZWRjLTJhMmM3MGI2YjY1NC5wbmc_WC1BbXotQWxnb3JpdGhtPUFXUzQtSE1BQy1TSEEyNTYmWC1BbXotQ3JlZGVudGlhbD1BS0lBVkNPRFlMU0E1M1BRSzRaQSUyRjIwMjYwMzA0JTJGdXMtZWFzdC0xJTJGczMlMkZhd3M0X3JlcXVlc3QmWC1BbXotRGF0ZT0yMDI2MDMwNFQxNzQ0MjBaJlgtQW16LUV4cGlyZXM9MzAwJlgtQW16LVNpZ25hdHVyZT1mNTZjYTMzZDM2MjMyMTRiN2E3ZWZkNzA4YTk1ODhkNmU0MzU2MjVmZWE1Mjg1NDMxM2FkYWQwYTg4OWI5OTljJlgtQW16LVNpZ25lZEhlYWRlcnM9aG9zdCJ9.hvhc8OZbUXx8Z9BT1cPDgOWEhe1X0Qj7bV4TDnIfr1A" />



## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests to the [GitHub repository](https://github.com/eithanwes/qgis-open-bus-stride-plugin).

## License

This project is licensed under the GNU General Public License v2.0 - see the [LICENSE](LICENSE) file for details.

## Author

**Eithan Weiss Schonberg**

