import ee
from datetime import datetime


PROJECT_ID = "gen-lang-client-0849641374"


LAND_COVER_CLASSES = {
    0: "Water",
    1: "Trees",
    2: "Grass",
    3: "Flooded Vegetation",
    4: "Crops",
    5: "Shrub & Scrub",
    6: "Built Area",
    7: "Bare Land",
    8: "Snow & Ice",
}


def initialize_earth_engine():

    ee.Initialize(
        project=PROJECT_ID
    )


def timestamp_to_date(timestamp):

    if timestamp is None:
        return None

    return (
        datetime
        .fromtimestamp(
            timestamp / 1000
        )
        .strftime("%Y-%m-%d")
    )


def get_geospatial_features(
    latitude: float,
    longitude: float
):

    initialize_earth_engine()

    point = ee.Geometry.Point([
        longitude,
        latitude
    ])


    # =================================================
    # DEFAULT RESULT
    # =================================================

    result = {

        "latitude": latitude,

        "longitude": longitude,

        "elevation_meters": None,

        "land_cover": None,

        "built_probability": None,

        "water_probability": None,

        "land_cover_date": None,

        "recent_precipitation_mm": None,

        "precipitation_date": None,
        "data_status": "live_earth_engine",
        "provider": "Google Earth Engine",

    }


    # =================================================
    # 1. SRTM ELEVATION
    # =================================================

    try:

        elevation_image = ee.Image(
            "USGS/SRTMGL1_003"
        )


        elevation_result = (
            elevation_image
            .select("elevation")
            .reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=point,
                scale=30,
                maxPixels=10000
            )
            .getInfo()
        )


        print(
            "SRTM result:",
            elevation_result
        )


        if elevation_result:

            elevation = (
                elevation_result.get(
                    "elevation"
                )
            )


            if elevation is not None:

                result[
                    "elevation_meters"
                ] = round(
                    float(elevation),
                    2
                )


    except Exception as e:

        print(
            "SRTM error:",
            e
        )


    # =================================================
    # 2. DYNAMIC WORLD
    # =================================================

    try:

        dynamic_world = (
            ee.ImageCollection(
                "GOOGLE/DYNAMICWORLD/V1"
            )
            .filterBounds(point)
            .filter(
                ee.Filter.notNull([
                    "system:time_start"
                ])
            )
            .sort(
                "system:time_start",
                False
            )
        )


        # Get a small number of recent images.
        # This avoids processing the entire collection.

        recent_images = (
            dynamic_world
            .limit(5)
            .toList(5)
        )


        # We know from testing that the first
        # two images may not contain usable pixels.
        # Check only five recent images.

        for index in range(5):

            try:

                image = ee.Image(
                    recent_images.get(index)
                )


                timestamp = (
                    image
                    .get(
                        "system:time_start"
                    )
                    .getInfo()
                )


                date = timestamp_to_date(
                    timestamp
                )


                pixel = (
                    image
                    .select([
                        "label",
                        "built",
                        "water"
                    ])
                    .reduceRegion(
                        reducer=ee.Reducer.first(),
                        geometry=point,
                        scale=10,
                        maxPixels=10000
                    )
                    .getInfo()
                )


                print(
                    f"Dynamic World "
                    f"{index + 1} "
                    f"({date}):",
                    pixel
                )


                if not pixel:

                    continue


                label = pixel.get(
                    "label"
                )

                built = pixel.get(
                    "built"
                )

                water = pixel.get(
                    "water"
                )


                # -------------------------------------
                # Accept this image if useful values
                # are available.
                # -------------------------------------

                if (
                    label is not None
                    or built is not None
                    or water is not None
                ):

                    if label is not None:

                        result[
                            "land_cover"
                        ] = (
                            LAND_COVER_CLASSES.get(
                                int(label),
                                "Unknown"
                            )
                        )


                    if built is not None:

                        result[
                            "built_probability"
                        ] = round(
                            float(built),
                            4
                        )


                    if water is not None:

                        result[
                            "water_probability"
                        ] = round(
                            float(water),
                            4
                        )


                    result[
                        "land_cover_date"
                    ] = date


                    # Stop once we have usable data.

                    break


            except Exception as image_error:

                print(
                    "Dynamic World image error:",
                    image_error
                )

                continue


    except Exception as e:

        print(
            "Dynamic World error:",
            e
        )


    # =================================================
    # 3. ERA5-LAND
    # =================================================

    try:

        era5 = (
            ee.ImageCollection(
                "ECMWF/ERA5_LAND/DAILY_AGGR"
            )
            .filterBounds(point)
            .sort(
                "system:time_start",
                False
            )
            .limit(1)
        )


        latest_era5 = ee.Image(
            era5.first()
        )


        timestamp = (
            latest_era5
            .get(
                "system:time_start"
            )
            .getInfo()
        )


        precipitation_date = (
            timestamp_to_date(
                timestamp
            )
        )


        precipitation_result = (
            latest_era5
            .select(
                "total_precipitation_sum"
            )
            .reduceRegion(
                reducer=ee.Reducer.first(),
                geometry=point,
                scale=11132,
                maxPixels=10000
            )
            .getInfo()
        )


        print(
            "ERA5 result:",
            precipitation_result
        )


        if precipitation_result:

            precipitation_m = (
                precipitation_result.get(
                    "total_precipitation_sum"
                )
            )


            if precipitation_m is not None:

                result[
                    "recent_precipitation_mm"
                ] = round(
                    float(
                        precipitation_m
                    ) * 1000,
                    2
                )


                result[
                    "precipitation_date"
                ] = precipitation_date


    except Exception as e:

        print(
            "ERA5 error:",
            e
        )


    # =================================================
    # FINAL RESULT
    # =================================================

    print(
        "FINAL GEOSPATIAL RESULT:",
        result
    )


    return result