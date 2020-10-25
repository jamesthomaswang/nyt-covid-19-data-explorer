import streamlit as st
import plotly.graph_objects as go

from pampy import match, _
# from toolz import pipe, curry, memoize, update_in, assoc, curried, first

from enum import Enum

import model


Series = Enum("Series", "CASES DEATHS")


def create_figure(traces=None, layout=None):
    return go.FigureWidget(data=traces, layout=layout)


def create_choropleth():
    trace_dict = {
        "locationmode": "geojson-id",
        "autocolorscale": False
    }

    layout = {
        "title": {"text": "Building..."},
        "geo": {
            "scope": "usa",
            "projection": {"type": "albers usa"},
            "showlakes": False,
            # "showland": False
        }
    }

    trace = go.Choropleth(trace_dict)

    return create_figure(trace, layout)


def update_choropleth(component, fig, granularity,
                      fips="", date="2020-09-27", series=Series.CASES):
    trace, layout = _build_trace_layout_update(granularity, fips, date, series)

    fig.update_traces(overwrite=True,
                      selector={"type": "choropleth"},
                      **trace)
    fig.update_layout(**layout)

    component.plotly_chart(fig, use_container_width=True)


def _build_trace_layout_update(granularity, fips, date, series):
    df = model.filter_covid_data(granularity, fips, date)
    geo = model.filter_geo_data(granularity, fips)

    (series_column, color_scale,
     line_color, series_text) = _choropleth_series_info(series)

    x = df.fips
    y = df[series_column]

    names = x.map(model.fips_name)

    trace = {
        "geojson": geo,
        "locations": x,
        "z": y,
        "zmin": y.min(),
        "zmax": y.max(),
        "colorscale": color_scale,
        "marker_line_color": line_color,
        "colorbar_title": series_text,
        "customdata": names,
        "hovertemplate": ("%{{customdata}} <br>"
                          "{}: %{{z:.0f}}").format(series_text),
        "visible": True
    }

    layout = {
        "title": {"text": _choropleth_title_text(series_text, fips, date)},
        "geo": {"fitbounds": "locations"}
    }

    # Automatic bounds fitting breaks when applied to Alaska (FIPS 02). I
    # suspect this is due to the fact that it straddles the International Date
    # Line. Therefore, when Alaska is selected, the map center and zoom level
    # need to be set manually.
    if fips == "02":
        layout["geo"]["fitbounds"] = False
        layout["geo"]["center"] = {"lat": 62, "lon": -162}
        layout["geo"]["projection"] = {"scale": 4}

    if granularity == model.Granularity.STATE:
        x_abbr = x.map(model.state_fips_abbr)
        trace["locationmode"] = "USA-states"
        trace["geojson"] = None
        trace["locations"] = x_abbr
        layout["geo"]["fitbounds"] = False

    return trace, layout


def _choropleth_series_info(series):
    return match(
        series,
        Series.CASES,  ("cases",  "Blues", "rgb(8,48,107)", "Number of Cases"),
        Series.DEATHS, ("deaths", "Reds", "rgb(103,0,13)", "Number of Deaths"),
        _,             (None, "Greens", "rgb(0,58,27)", None)
    )


def _choropleth_title_text(series_text, fips, date):
    return (
        "{} in {}<br>"
        "on {}"
    ).format(
        series_text,
        model.fips_name(fips),
        date
    )


def create_line():
    traces = [
        go.Scatter(name="Cases", mode="lines",
                   line_color="rgb(8,48,107)"),
        go.Scatter(name="Deaths", mode="lines",
                   line_color="rgb(165,15,21)")
    ]

    layout = {
        "title": {"text": "Building..."}
    }

    return create_figure(traces, layout)


def update_line(component, fig, granularity, fips=""):
    df = model.filter_covid_data(granularity, fips)

    x = df.date
    y_cases = df.cases
    y_deaths = df.deaths

    fig.update_traces(overwrite=True,
                      selector={"name": "Cases"},
                      x=x,
                      y=y_cases)

    fig.update_traces(overwrite=True,
                      selector={"name": "Deaths"},
                      x=x,
                      y=y_deaths)

    fig.update_layout(
        title=_line_title_text(fips),
        xaxis_title="Date",
        yaxis_title="Number of Cases/Deaths",
        hovermode="x unified"
    )

    component.plotly_chart(fig, use_container_width=True)


def _line_title_text(fips):
    return (
        "Number of Cases & Deaths from COVID-19<br>"
        "in {}"
    ).format(model.fips_name(fips))


# GUI State

gui_state = {
    "series": Series.CASES,
    "date": "2020-09-27",
    "state_fips": "42",
    "county_fips": "42003"
}


# Create GUI

st.beta_set_page_config(
    page_title="New York Times U.S. COVID-19 Dataset Explorer",
    layout="wide"
)

st.title("New York Times U.S. COVID-19 Dataset Explorer")


# Country GUI Row

st.subheader("U.S. Cases & Deaths")

st_country_map_col, st_country_line = st.beta_columns(2)

country_map = create_choropleth()
st_country_map = st_country_map_col.plotly_chart(
    country_map, use_container_width=True)

st_country_map_col.markdown(
    "***Due to a Plotly bug, you need to click on the `reset` button on "
    "the top-right corner of the country map above for the data to show up"
    "after every change.***"
)

country_line = create_line()


# State GUI Row

st.subheader("State Cases & Deaths")

st_state_map_col, st_state_line = st.beta_columns(2)

state_map = create_choropleth()
st_state_map = st_state_map_col.plotly_chart(
    state_map, use_container_width=True)

state_line = create_line()


# County GUI Row

st.subheader("County Cases & Deaths")

st_county_line = st.beta_columns(2)[1]

county_line = create_line()

st.markdown(
    "*Map files created by the US Census Bureau and converted to GeoJSON "
    "format by[Eric Celeste](https: // eric.clst.org/tech/usgeojson /) .*"
    "\n\n"
    "*Coronavirus data by "
    "[The New York Times](https://github.com/nytimes/covid-19-data).*")


# Sidebar

st_series = st.sidebar.radio(
    "Data Type", [Series.CASES, Series.DEATHS],
    index=(gui_state["series"] == Series.DEATHS),
    format_func=lambda x: match(x,
                                Series.CASES, "Show Cases",
                                Series.DEATHS, "Show Deaths")
)

st_state = st.sidebar.selectbox(
    "State", list(model.fips_data().fips.sort_values()), index=38,
    format_func=lambda x: model.fips_name(x)
)

st_county_container = st.sidebar.empty()


def update_st_county():
    global gui_state
    global st_county
    st_county = st_county_container.selectbox(
        "County",
        sorted(list(
            model.filter_covid_data(model.Granularity.COUNTY,
                                    fips=gui_state["state_fips"],
                                    date=gui_state["date"])
            .fips
            .unique()
        )),
        index=1,
        format_func=lambda x: model.fips_name(x)
    )


# Update Functions

update_country_map = (
    lambda: update_choropleth(
        st_country_map, country_map, model.Granularity.STATE,
        date=gui_state["date"], series=gui_state["series"]))
update_state_map = (
    lambda: update_choropleth(
        st_state_map, state_map, model.Granularity.COUNTY,
        fips=gui_state["state_fips"], date=gui_state["date"],
        series=gui_state["series"]))

update_country_line = (
    lambda: update_line(st_country_line, country_line,
                        model.Granularity.COUNTRY))
update_state_line = (
    lambda: update_line(st_state_line, state_line, model.Granularity.STATE,
                        fips=gui_state["state_fips"]))
update_county_line = (
    lambda: update_line(st_county_line, county_line, model.Granularity.COUNTY,
                        fips=gui_state["county_fips"])
)


def update_choropleths():
    update_country_map()
    update_state_map()


def update_lines():
    update_country_line()
    update_state_line()
    update_county_line()


def update_country_row():
    update_country_map()
    update_country_line()


def update_state_row():
    update_state_map()
    update_state_line()


def update_all():
    update_choropleths()
    update_lines()


# Click Callbacks

if st_series:
    gui_state["series"] = st_series
    update_choropleths()

if st_state:
    gui_state["state_fips"] = st_state
    update_st_county()
    update_state_row()

if st_county:
    print(st_county)
    gui_state["county_fips"] = st_county
    update_county_line()

update_country_line()
