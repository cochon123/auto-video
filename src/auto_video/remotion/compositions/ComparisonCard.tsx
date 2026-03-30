import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { z } from "zod";

export const ComparisonCardSchema = z.object({
  headline: z.string(),
  leftTitle: z.string(),
  leftBody: z.string(),
  rightTitle: z.string(),
  rightBody: z.string(),
  accentColor: z.string().default("#4ecdc4"),
  backgroundColor: z.string().default("#111827"),
});

export type ComparisonCardProps = z.infer<typeof ComparisonCardSchema>;

export const ComparisonCard: React.FC<ComparisonCardProps> = ({
  headline,
  leftTitle,
  leftBody,
  rightTitle,
  rightBody,
  accentColor,
  backgroundColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const leftProgress = spring({ frame: frame - 6, fps, config: { damping: 13, stiffness: 120 } });
  const rightProgress = spring({ frame: frame - 16, fps, config: { damping: 13, stiffness: 120 } });
  const headlineOpacity = interpolate(frame, [0, 15], [0, 1]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor,
        color: "white",
        padding: 72,
        fontFamily: "Inter, sans-serif",
      }}
    >
      <div style={{ marginBottom: 48, opacity: headlineOpacity }}>
        <div
          style={{
            fontSize: 24,
            letterSpacing: 5,
            textTransform: "uppercase",
            color: accentColor,
            marginBottom: 12,
          }}
        >
          Comparison
        </div>
        <div style={{ fontSize: 68, fontWeight: 700, lineHeight: 1.05 }}>{headline}</div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 120px 1fr", gap: 24, alignItems: "stretch" }}>
        <ComparisonPane
          title={leftTitle}
          body={leftBody}
          accentColor={accentColor}
          direction={-1}
          progress={leftProgress}
        />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", fontSize: 72, fontWeight: 800, color: accentColor }}>
          VS
        </div>
        <ComparisonPane
          title={rightTitle}
          body={rightBody}
          accentColor={accentColor}
          direction={1}
          progress={rightProgress}
        />
      </div>
    </AbsoluteFill>
  );
};

type ComparisonPaneProps = {
  title: string;
  body: string;
  accentColor: string;
  direction: -1 | 1;
  progress: number;
};

const ComparisonPane: React.FC<ComparisonPaneProps> = ({
  title,
  body,
  accentColor,
  direction,
  progress,
}) => {
  return (
    <div
      style={{
        backgroundColor: "rgba(255,255,255,0.05)",
        border: `1px solid ${accentColor}44`,
        borderRadius: 28,
        padding: 28,
        transform: `translateX(${(1 - progress) * direction * 80}px)`,
        opacity: progress,
      }}
    >
      <div style={{ fontSize: 18, textTransform: "uppercase", letterSpacing: 4, color: accentColor, marginBottom: 16 }}>
        Side
      </div>
      <div style={{ fontSize: 44, fontWeight: 700, marginBottom: 16 }}>{title}</div>
      <div style={{ fontSize: 28, lineHeight: 1.35, color: "#d1d5db" }}>{body}</div>
    </div>
  );
};
