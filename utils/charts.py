"""
VoltSense 5G - Interactive Plotly Visualization Components
Generates enterprise-grade energy analytics charts with dark theme aesthetics matching VoltSense design system.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any

from config import COLORS

DARK_THEME_LAYOUT = dict(
    paper_bgcolor="rgba(15, 23, 42, 0.95)",
    plot_bgcolor="rgba(30, 41, 59, 0.4)",
    font=dict(family="Inter, sans-serif", color="#E2E8F0", size=12),
    margin=dict(l=40, r=30, t=40, b=40),
    xaxis=dict(
        gridcolor="rgba(51, 65, 85, 0.5)",
        linecolor="#334155",
        zerolinecolor="rgba(51, 65, 85, 0.5)",
        tickfont=dict(color="#94A3B8")
    ),
    yaxis=dict(
        gridcolor="rgba(51, 65, 85, 0.5)",
        linecolor="#334155",
        zerolinecolor="rgba(51, 65, 85, 0.5)",
        tickfont=dict(color="#94A3B8")
    ),
    legend=dict(
        bgcolor="rgba(15, 23, 42, 0.8)",
        bordercolor="#334155",
        borderwidth=1,
        font=dict(color="#CBD5E1")
    )
)


def create_gauge_chart(
    value: float, 
    title: str, 
    min_val: float, 
    max_val: float, 
    unit: str,
    warning_val: Optional[float] = None,
    danger_val: Optional[float] = None,
    color_bar: str = COLORS["cyan"]
) -> go.Figure:
    """Creates a modern industrial circular gauge for real-time telemetry."""
    steps = [
        {'range': [min_val, max_val * 0.7], 'color': "rgba(16, 185, 129, 0.15)"},
        {'range': [max_val * 0.7, max_val * 0.88], 'color': "rgba(245, 158, 11, 0.2)"},
        {'range': [max_val * 0.88, max_val], 'color': "rgba(239, 68, 68, 0.25)"}
    ]
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': f"<b>{title}</b><br><span style='font-size:0.8em;color:#94A3B8'>{unit}</span>", 'font': {'size': 14, 'color': '#E2E8F0'}},
        number={'suffix': f" {unit}", 'font': {'size': 22, 'color': '#F8FAFC', 'family': 'JetBrains Mono'}},
        gauge={
            'axis': {'range': [min_val, max_val], 'tickcolor': "#64748B"},
            'bar': {'color': color_bar, 'thickness': 0.25},
            'bgcolor': "rgba(30, 41, 59, 0.8)",
            'borderwidth': 1,
            'bordercolor': "#334155",
            'steps': steps,
            'threshold': {
                'line': {'color': "#EF4444", 'width': 3},
                'thickness': 0.75,
                'value': danger_val if danger_val else max_val * 0.95
            }
        }
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=15, r=15, t=30, b=15),
        height=210
    )
    return fig


def create_realtime_power_chart(df: pd.DataFrame) -> go.Figure:
    """Renders active power (W) and apparent power (VA) live telemetry pulse."""
    fig = go.Figure()

    if not df.empty:
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df["active_power"],
            mode="lines",
            name="Active Power P (W)",
            line=dict(color=COLORS["cyan"], width=2.5),
            fill="tozeroy",
            fillcolor="rgba(6, 182, 212, 0.08)"
        ))
        
        if "apparent_power" in df.columns:
            fig.add_trace(go.Scatter(
                x=df["timestamp"],
                y=df["apparent_power"],
                mode="lines",
                name="Apparent Power S (VA)",
                line=dict(color=COLORS["electric_blue"], width=1.5, dash="dash")
            ))

    fig.update_layout(
        **DARK_THEME_LAYOUT,
        title="<b>Real-Time Electrical Power Telemetry Stream (Active P vs Apparent S)</b>",
        xaxis_title="Timestamp",
        yaxis_title="Power (Watts / VA)",
        hovermode="x unified",
        height=340
    )
    return fig


def create_multi_parameter_chart(df: pd.DataFrame) -> go.Figure:
    """Subplots for Voltage, Current, Frequency, and Power Factor."""
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Grid Voltage (V)", "Load Current (A)", "Grid Frequency (Hz)", "Power Factor (cos φ)"),
        vertical_spacing=0.18,
        horizontal_spacing=0.10
    )

    if not df.empty:
        # Voltage
        fig.add_trace(
            go.Scatter(x=df["timestamp"], y=df["voltage"], mode="lines", name="Voltage (V)", line=dict(color="#38BDF8", width=1.8)),
            row=1, col=1
        )
        # 230V reference line
        fig.add_hline(y=230.0, line_dash="dot", line_color="rgba(148, 163, 184, 0.6)", row=1, col=1)

        # Current
        fig.add_trace(
            go.Scatter(x=df["timestamp"], y=df["current"], mode="lines", name="Current (A)", line=dict(color="#F59E0B", width=1.8)),
            row=1, col=2
        )

        # Frequency
        fig.add_trace(
            go.Scatter(x=df["timestamp"], y=df["frequency"], mode="lines", name="Frequency (Hz)", line=dict(color="#10B981", width=1.8)),
            row=2, col=1
        )
        # 50Hz reference line
        fig.add_hline(y=50.0, line_dash="dot", line_color="rgba(148, 163, 184, 0.6)", row=2, col=1)

        # Power Factor
        fig.add_trace(
            go.Scatter(x=df["timestamp"], y=df["power_factor"], mode="lines", name="Power Factor", line=dict(color="#A855F7", width=1.8)),
            row=2, col=2
        )
        # 0.90 threshold line
        fig.add_hline(y=0.90, line_dash="dash", line_color="rgba(239, 68, 68, 0.6)", row=2, col=2)

    fig.update_layout(
        **DARK_THEME_LAYOUT,
        height=480,
        showlegend=False,
        hovermode="x unified"
    )
    return fig


def create_diurnal_hourly_chart(df_hourly: pd.DataFrame) -> go.Figure:
    """Renders 24-hour diurnal profile of typical electrical usage."""
    fig = go.Figure()

    if not df_hourly.empty:
        # Shaded band for min-max envelope
        fig.add_trace(go.Scatter(
            x=list(df_hourly["hour"]) + list(df_hourly["hour"])[::-1],
            y=list(df_hourly["max_power_w"]) + list(df_hourly["min_power_w"])[::-1],
            fill='toself',
            fillcolor='rgba(37, 99, 235, 0.15)',
            line=dict(color='rgba(255,255,255,0)'),
            name='Daily Min-Max Envelope',
            hoverinfo="skip"
        ))
        
        # Mean load line
        fig.add_trace(go.Scatter(
            x=df_hourly["hour"],
            y=df_hourly["avg_power_w"],
            mode="lines+markers",
            name="Average Power (W)",
            line=dict(color=COLORS["cyan"], width=3),
            marker=dict(size=6, color="#38BDF8")
        ))

    fig.update_layout(
        **DARK_THEME_LAYOUT,
        title="<b>24-Hour Diurnal Load Profile (Campus Daily Cycle)</b>",
        xaxis=dict(
            title="Hour of Day (0:00 to 23:00)",
            tickmode="linear",
            tick0=0,
            dtick=2,
            gridcolor="rgba(51, 65, 85, 0.5)"
        ),
        yaxis_title="Active Power (W)",
        height=350,
        hovermode="x unified"
    )
    return fig


def create_daily_consumption_bar_chart(df_daily: pd.DataFrame, tariff_rate: float) -> go.Figure:
    """Bar chart with dual axis showing daily kWh and total daily estimated cost."""
    fig = go.Figure()

    if not df_daily.empty:
        # Aggregate by date if multiple devices exist
        daily_summary = df_daily.groupby("date").agg({
            "daily_energy_kwh": "sum",
            "peak_power_w": "max"
        }).reset_index()

        daily_summary["cost_inr"] = daily_summary["daily_energy_kwh"] * tariff_rate

        fig.add_trace(go.Bar(
            x=daily_summary["date"],
            y=daily_summary["daily_energy_kwh"],
            name="Energy (kWh)",
            marker=dict(
                color=daily_summary["daily_energy_kwh"],
                colorscale="Blues",
                line=dict(color="#38BDF8", width=1)
            ),
            yaxis="y"
        ))

        fig.add_trace(go.Scatter(
            x=daily_summary["date"],
            y=daily_summary["cost_inr"],
            name=f"Est. Bill (₹ @ ₹{tariff_rate}/kWh)",
            mode="lines+markers",
            line=dict(color=COLORS["amber"], width=2.5),
            marker=dict(size=6, color="#F59E0B"),
            yaxis="y2"
        ))

    fig.update_layout(
        **DARK_THEME_LAYOUT,
        title="<b>Daily Energy Consumption (kWh) and Estimated Electricity Costs (₹)</b>",
        xaxis_title="Date",
        yaxis=dict(title="Energy Consumption (kWh)", gridcolor="rgba(51, 65, 85, 0.5)"),
        yaxis2=dict(
            title="Estimated Cost (₹)",
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(color="#F59E0B")
        ),
        legend=dict(x=0.01, y=0.99),
        height=380,
        hovermode="x unified"
    )
    return fig


def create_device_breakdown_pie(df: pd.DataFrame) -> go.Figure:
    """Pie/Donut chart breaking down energy usage across devices/locations."""
    if df.empty:
        return go.Figure()

    dev_summary = df.groupby(["building", "device_name"])["energy_kwh"].agg(
        lambda s: max(0.0, s.max() - s.min()) if len(s) > 1 else s.sum()
    ).reset_index()

    if dev_summary["energy_kwh"].sum() <= 0:
        # fallback to active power share
        dev_summary = df.groupby(["building", "device_name"])["active_power"].mean().reset_index()
        dev_summary.rename(columns={"active_power": "energy_kwh"}, inplace=True)

    fig = px.pie(
        dev_summary,
        names="device_name",
        values="energy_kwh",
        hole=0.55,
        color_discrete_sequence=["#2563EB", "#06B6D4", "#10B981", "#8B5CF6", "#F59E0B", "#EC4899"]
    )
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        marker=dict(line=dict(color='#0F172A', width=2))
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0"),
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=False
    )
    return fig


def create_anomaly_scatter_chart(readings_df: pd.DataFrame, anomalies_df: pd.DataFrame) -> go.Figure:
    """Overlay plot of continuous telemetry with detected anomalies highlighted as alert markers."""
    fig = go.Figure()

    if not readings_df.empty:
        fig.add_trace(go.Scatter(
            x=readings_df["timestamp"],
            y=readings_df["active_power"],
            mode="lines",
            name="Monitored Load P (W)",
            line=dict(color="#38BDF8", width=1.5),
            opacity=0.85
        ))

    if not anomalies_df.empty:
        # Match anomalies with reading timestamps
        for severity, color, symbol in [
            ("CRITICAL", "#EF4444", "triangle-up"),
            ("MEDIUM", "#F59E0B", "diamond"),
            ("LOW", "#38BDF8", "circle")
        ]:
            subset = anomalies_df[anomalies_df["severity"] == severity]
            if not subset.empty:
                fig.add_trace(go.Scatter(
                    x=subset["timestamp"],
                    y=subset["detected_value"],
                    mode="markers",
                    name=f"{severity} Anomaly",
                    marker=dict(size=11, color=color, symbol=symbol, line=dict(color="#FFFFFF", width=1)),
                    text=[f"{r.reason}<br>Method: {r.detection_method}" for _, r in subset.iterrows()],
                    hoverinfo="text+x+y"
                ))

    fig.update_layout(
        **DARK_THEME_LAYOUT,
        title="<b>Telemetry Stream with Flagged Outlier / Anomaly Events</b>",
        xaxis_title="Timestamp",
        yaxis_title="Detected Parameter Value",
        height=380,
        hovermode="closest"
    )
    return fig


def create_forecast_chart(
    hist_df: pd.DataFrame, 
    forecast_df: pd.DataFrame, 
    model_name: str
) -> go.Figure:
    """Visualizes historical actuals vs predicted horizon with uncertainty bands."""
    fig = go.Figure()

    # Recent historical actuals (up to last 7 days)
    if not hist_df.empty:
        recent_hist = hist_df.tail(168)  # last 7 days of hourly
        fig.add_trace(go.Scatter(
            x=recent_hist["timestamp"],
            y=recent_hist["energy_kwh"],
            mode="lines",
            name="Historical Actual (kWh)",
            line=dict(color="#94A3B8", width=2)
        ))

    if not forecast_df.empty:
        # Forecast confidence band if bounds present
        if "upper_bound_kwh" in forecast_df.columns and "lower_bound_kwh" in forecast_df.columns:
            fig.add_trace(go.Scatter(
                x=list(forecast_df["target_date"]) + list(forecast_df["target_date"])[::-1],
                y=list(forecast_df["upper_bound_kwh"]) + list(forecast_df["lower_bound_kwh"])[::-1],
                fill='toself',
                fillcolor='rgba(16, 185, 129, 0.15)',
                line=dict(color='rgba(255,255,255,0)'),
                name='95% Confidence Band',
                hoverinfo="skip"
            ))

        # Predicted line
        fig.add_trace(go.Scatter(
            x=forecast_df["target_date"],
            y=forecast_df["predicted_energy_kwh"],
            mode="lines+markers",
            name=f"Forecast: {model_name}",
            line=dict(color=COLORS["emerald"], width=2.8, dash="solid"),
            marker=dict(size=5, color="#34D399")
        ))

    fig.update_layout(
        **DARK_THEME_LAYOUT,
        title=f"<b>Electricity Consumption Forecast ({model_name}) with Uncertainty Intervals</b>",
        xaxis_title="Timeline",
        yaxis_title="Energy Consumption (kWh)",
        height=380,
        hovermode="x unified"
    )
    return fig


def create_model_comparison_bar_chart(metrics_df: pd.DataFrame) -> go.Figure:
    """Bar chart comparing MAE, RMSE, and R2 across tested ML algorithms."""
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("MAE (Mean Absolute Error)", "RMSE (Root Mean Sq Error)", "R² Score (Goodness of Fit)"),
        horizontal_spacing=0.1
    )

    colors = ["#2563EB", "#06B6D4", "#10B981"]

    if not metrics_df.empty:
        # MAE (lower is better)
        fig.add_trace(
            go.Bar(x=metrics_df["model"], y=metrics_df["mae"], marker_color=colors, showlegend=False),
            row=1, col=1
        )
        # RMSE (lower is better)
        fig.add_trace(
            go.Bar(x=metrics_df["model"], y=metrics_df["rmse"], marker_color=colors, showlegend=False),
            row=1, col=2
        )
        # R2 (higher is better)
        fig.add_trace(
            go.Bar(x=metrics_df["model"], y=metrics_df["r2"], marker_color=colors, showlegend=False),
            row=1, col=3
        )

    fig.update_layout(
        **DARK_THEME_LAYOUT,
        height=320,
        title="<b>Machine Learning Algorithm Benchmark (Chrono Train/Test Split)</b>"
    )
    return fig


def create_5g_latency_chart(protocol_data: List[Dict[str, Any]]) -> go.Figure:
    """Compares simulated 5G slice latencies vs 4G legacy connection."""
    df_slices = pd.DataFrame(protocol_data)
    fig = px.bar(
        df_slices,
        x="slice_name",
        y="latency_ms",
        color="slice_name",
        text="latency_ms",
        color_discrete_sequence=["#06B6D4", "#2563EB", "#10B981", "#64748B"]
    )
    fig.update_traces(texttemplate='%{text:.1f} ms', textposition='outside')
    fig.update_layout(
        **DARK_THEME_LAYOUT,
        title="<b>3GPP Release-16 Network Slicing Latency Profiles (Simulated)</b>",
        xaxis_title="5G Network Slice Profile",
        yaxis_title="Estimated Latency (ms)",
        showlegend=False,
        height=320
    )
    return fig
