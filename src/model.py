from pampy import match
from toolz import (pipe, curry, memoize, update_in,
                   assoc, curried, first, excepts)

import pandas as pd

import json
from enum import IntEnum


Granularity = IntEnum("Granularity", {"COUNTRY": 0, "STATE": 2, "COUNTY": 5})


def _covid_filepath(granularity):
    return match(
        granularity,
        Granularity.COUNTRY, "data/us.csv",
        Granularity.STATE,   "data/us-states.csv",
        Granularity.COUNTY,  "data/us-counties.csv"
    )


def _geo_filepath(granularity):
    return match(
        granularity,
        Granularity.STATE,  "data/gz_2010_us_040_00_20m.json",
        Granularity.COUNTY, "data/gz_2010_us_050_00_20m.json"
    )


fips_filepath = "data/us-state-ansi-fips.csv"


@memoize
def covid_data(granularity):
    """Read a coronavirus data file.

    Note: Impure Function
    Reasons:
        Non-deterministic: The return value relys on file contents, which can
            change arbitrarily.

    Args:
        granularity (<enum "Granularity">): The granularity of the data file.

    Returns:
        pd.DataFrame: The contents of the data file, with correct dtypes for
            "date" and "fips" columns.
    """
    return pipe(
        granularity,
        _covid_filepath,
        curry(pd.read_csv,
              parse_dates=["date"],
              dtype={"fips": pd.StringDtype()})
    )


@memoize
def filter_covid_data(granularity, fips=None, date=None):
    data = covid_data(granularity)
    if fips is not None and "fips" in data:
        data = _filter_covid_data_by_fips(data, fips)
    if date is not None:
        data = _filter_covid_data_by_date(data, date)
    return data


def _filter_covid_data_by_fips(data, fips):
    return data[data.fips.str.startswith(fips)]


def _filter_covid_data_by_date(data, date):
    return data[data.date == date]


@memoize
def geo_data(granularity, encoding="ISO-8859-1"):
    return pipe(
        granularity,
        _geo_filepath,
        _read_json_file,
        _format_geo_data
    )


def _read_json_file(filepath, encoding="ISO-8859-1"):
    with open(filepath, encoding=encoding) as response:
        return json.load(response)


def _format_geo_data(data):
    for i in range(len(data["features"])):
        data["features"][i]["id"] = _geo_region_id(
            data["features"][i]["properties"])
    return data


"""update_in(
        data,
        ["features"],
        lambda regions: list(map(_format_geo_region, regions))
    )"""


def _format_geo_region(region):
    return assoc(
        region,
        "id",
        _geo_region_id(region["properties"])
    )


def _geo_region_id(properties):
    if "COUNTY" in properties:
        return "{}{}".format(properties["STATE"],
                             properties["COUNTY"])
    else:
        return str(properties["STATE"])


@memoize
def filter_geo_data(granularity, fips):
    return update_in(
        geo_data(granularity),
        ["features"],
        curry(_filter_geojson_regions, fips=fips)
    )


def _filter_geojson_regions(regions, fips):
    return list(filter(lambda region: region["id"].startswith(fips), regions))


@memoize
def fips_data():
    return pd.read_csv(fips_filepath,
                       dtype={"fips": pd.StringDtype()},
                       names=["name", "fips", "abbr"],
                       skiprows=1)


def fips_at_larger_granularity(fips, granularity):
    return fips[:granularity]


@memoize
def fips_name(fips):
    return match(
        len(fips),
        int(Granularity.COUNTRY), "The United States",
        int(Granularity.STATE), lambda _:
            _state_fips_name(fips),
        int(Granularity.COUNTY), lambda _:
            "{}, {}".format(
                _county_fips_name(fips),
                fips_name(fips_at_larger_granularity(fips, Granularity.STATE))
        )
    )


def _state_fips_name(fips):
    data = fips_data()
    rows = data[data.fips == fips]
    if len(rows) < 1:
        return "Unknown"
    return rows.name.iloc[0]


def _county_fips_name(fips):
    return pipe(
        Granularity.COUNTY,
        geo_data,
        curried.get("features"),
        curry(filter, lambda region: region["id"] == fips),
        excepts(StopIteration,
                lambda x:
                    pipe(x, first, curried.get_in(["properties", "NAME"])),
                lambda _:
                    None
                )
    )


@memoize
def state_fips_abbr(fips):
    data = fips_data()
    rows = data[data.fips == fips]
    if len(rows) < 1:
        return "Unknown"
    return rows.abbr.iloc[0]
