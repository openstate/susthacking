#!/usr/bin/env bash

ogr2ogr -f GeoJSON ../bestand-veehouderijbedrijven.json -s_srs EPSG:28992 -t_srs EPSG:4326 WFS:"http://services.inspire-provincies.nl/AgriculturalAndAquacultureFacilities/services/download_AF"