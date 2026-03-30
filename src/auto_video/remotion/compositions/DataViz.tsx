/**
 * Data Visualization composition - Animated charts and graphs.
 */

import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring
} from "remotion";

interface DataPoint {
  label: string;
  value: number;
  color?: string;
}

interface DataVizProps {
  data: DataPoint[];
  chartType: "bar" | "line" | "pie";
  title?: string;
}

export const DataViz: React.FC<DataVizProps> = ({
  data,
  chartType,
  title
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const maxValue = Math.max(...data.map((d) => d.value), 1);

  // Title animation
  const titleOpacity = interpolate(frame, [0, 30], [0, 1]);

  if (chartType === "bar") {
    return <BarChart data={data} maxValue={maxValue} frame={frame} fps={fps} title={title} titleOpacity={titleOpacity} />;
  }

  if (chartType === "line") {
    return <LineChart data={data} maxValue={maxValue} frame={frame} fps={fps} title={title} titleOpacity={titleOpacity} />;
  }

  return null; // TODO: Implement pie chart
};

interface BarChartProps {
  data: DataPoint[];
  maxValue: number;
  frame: number;
  fps: number;
  title?: string;
  titleOpacity: number;
}

const BarChart: React.FC<BarChartProps> = ({ data, maxValue, frame, fps, title, titleOpacity }) => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#1a1a2e", padding: 100 }}>
      {title && (
        <div
          style={{
            fontSize: 48,
            fontWeight: "bold",
            color: "white",
            marginBottom: 50,
            opacity: titleOpacity
          }}
        >
          {title}
        </div>
      )}

      <div
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "flex-end",
          justifyContent: "space-around",
          height: 600,
          gap: 20
        }}
      >
        {data.map((item, index) => {
          const barHeight = spring({
            frame: frame - index * 10,
            fps,
            config: { damping: 15, stiffness: 80 }
          }) * (item.value / maxValue) * 600;

          const labelOpacity = interpolate(
            frame,
            [60 + index * 10, 80 + index * 10],
            [0, 1]
          );

          const valueOpacity = interpolate(
            frame,
            [70 + index * 10, 90 + index * 10],
            [0, 1]
          );

          return (
            <div
              key={index}
              style={{
                position: "relative",
                width: 80,
                height: 600,
                display: "flex",
                flexDirection: "column",
                justifyContent: "flex-end"
              }}
            >
              {/* Bar */}
              <div
                style={{
                  width: "100%",
                  height: barHeight,
                  backgroundColor: item.color || "#4ecdc4",
                  borderRadius: "8px 8px 0 0",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.3)"
                }}
              />

              {/* Label */}
              <div
                style={{
                  marginTop: 15,
                  fontSize: 20,
                  color: "white",
                  textAlign: "center",
                  opacity: labelOpacity,
                  fontWeight: 500
                }}
              >
                {item.label}
              </div>

              {/* Value */}
              <div
                style={{
                  fontSize: 24,
                  fontWeight: "bold",
                  color: item.color || "#4ecdc4",
                  textAlign: "center",
                  opacity: valueOpacity
                }}
              >
                {item.value}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

interface LineChartProps {
  data: DataPoint[];
  maxValue: number;
  frame: number;
  fps: number;
  title?: string;
  titleOpacity: number;
}

const LineChart: React.FC<LineChartProps> = ({ data, maxValue, frame, fps, title, titleOpacity }) => {
  // Calculate points for the line
  const chartWidth = 1400;
  const chartHeight = 500;
  const padding = 100;

  const points = data.map((item, index) => {
    const x = padding + (index / (data.length - 1)) * chartWidth;
    const y = 600 - padding - (item.value / maxValue) * chartHeight;
    return { x, y, ...item };
  });

  return (
    <AbsoluteFill style={{ backgroundColor: "#1a1a2e", padding: 100 }}>
      {title && (
        <div
          style={{
            fontSize: 48,
            fontWeight: "bold",
            color: "white",
            marginBottom: 50,
            opacity: titleOpacity
          }}
        >
          {title}
        </div>
      )}

      <svg
        width="1720"
        height="600"
        style={{
          position: "absolute",
          top: 200,
          left: 100
        }}
      >
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = 600 - padding - ratio * chartHeight;
          const opacity = interpolate(frame, [0, 30], [0, 0.2]);
          return (
            <line
              key={ratio}
              x1={padding}
              y1={y}
              x2={padding + chartWidth}
              y2={y}
              stroke="white"
              strokeWidth="1"
              opacity={opacity}
            />
          );
        })}

        {/* Line path */}
        <polyline
          points={points
            .map((p, i) => {
              const pointFrame = frame - i * 5;
              if (pointFrame < 0) return null;
              return `${p.x},${p.y}`;
            })
            .filter(Boolean)
            .join(" ")}
          fill="none"
          stroke="#4ecdc4"
          strokeWidth="4"
          opacity={interpolate(frame, [0, 30], [0, 1])}
        />

        {/* Data points */}
        {points.map((point, index) => {
          const pointFrame = frame - index * 5;
          const scale = spring({
            frame: pointFrame > 0 ? pointFrame - 30 : 0,
            fps,
            config: { damping: 10, stiffness: 100 }
          });

          if (pointFrame < 0) return null;

          return (
            <g key={index}>
              <circle
                cx={point.x}
                cy={point.y}
                r={8 * scale}
                fill={point.color || "#4ecdc4"}
                opacity={interpolate(pointFrame, [30, 50], [0, 1])}
              />
              <text
                x={point.x}
                y={point.y - 20}
                fill="white"
                fontSize="20"
                textAnchor="middle"
                opacity={interpolate(pointFrame, [50, 70], [0, 1])}
              >
                {point.value}
              </text>
              <text
                x={point.x}
                y={630}
                fill="white"
                fontSize="18"
                textAnchor="middle"
                opacity={interpolate(pointFrame, [70, 90], [0, 1])}
              >
                {point.label}
              </text>
            </g>
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};
