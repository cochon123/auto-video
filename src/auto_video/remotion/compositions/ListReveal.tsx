import React from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { z } from "zod";

export const ListRevealItemSchema = z.object({
  title: z.string(),
  subtitle: z.string().nullable().optional(),
  imagePath: z.string().nullable().optional(),
});

export const ListRevealSchema = z.object({
  title: z.string(),
  items: z.array(ListRevealItemSchema).min(1).max(6),
  accentColor: z.string().default("#4ecdc4"),
  backgroundColor: z.string().default("#0f172a"),
});

export type ListRevealProps = z.infer<typeof ListRevealSchema>;

export const ListReveal: React.FC<ListRevealProps> = ({
  title,
  items,
  accentColor,
  backgroundColor,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const titleOpacity = interpolate(frame, [0, 15], [0, 1]);
  const itemWindow = Math.max(Math.floor(durationInFrames / items.length), 24);

  return (
    <AbsoluteFill
      style={{
        backgroundColor,
        padding: 80,
        color: "white",
        fontFamily: "Inter, sans-serif",
      }}
    >
      <div style={{ opacity: titleOpacity, marginBottom: 48 }}>
        <div
          style={{
            fontSize: 26,
            letterSpacing: 6,
            textTransform: "uppercase",
            color: accentColor,
            marginBottom: 12,
          }}
        >
          Motion List
        </div>
        <div style={{ fontSize: 72, fontWeight: 700, lineHeight: 1.05 }}>{title}</div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {items.map((item, index) => (
          <Sequence key={`${item.title}-${index}`} from={index * Math.floor(itemWindow * 0.6)}>
            <RevealCard
              title={item.title}
              subtitle={item.subtitle ?? null}
              imagePath={item.imagePath ?? null}
              accentColor={accentColor}
              fps={fps}
            />
          </Sequence>
        ))}
      </div>
    </AbsoluteFill>
  );
};

type RevealCardProps = {
  title: string;
  subtitle: string | null;
  imagePath: string | null;
  accentColor: string;
  fps: number;
};

const RevealCard: React.FC<RevealCardProps> = ({
  title,
  subtitle,
  imagePath,
  accentColor,
  fps,
}) => {
  const frame = useCurrentFrame();
  const slide = spring({ frame, fps, config: { damping: 14, stiffness: 110 } });
  const opacity = interpolate(frame, [0, 12], [0, 1]);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: imagePath ? "240px 1fr" : "1fr",
        gap: 24,
        alignItems: "center",
        opacity,
        transform: `translateY(${(1 - slide) * 40}px)`,
        backgroundColor: "rgba(255,255,255,0.06)",
        border: `1px solid ${accentColor}55`,
        borderRadius: 28,
        padding: 24,
        backdropFilter: "blur(12px)",
      }}
    >
      {imagePath ? (
        <div style={{ width: 240, height: 160, overflow: "hidden", borderRadius: 20 }}>
          <Img
            src={imagePath}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>
      ) : null}
      <div>
        <div style={{ fontSize: 42, fontWeight: 700, marginBottom: 8 }}>{title}</div>
        {subtitle ? <div style={{ fontSize: 24, color: "#d1d5db" }}>{subtitle}</div> : null}
      </div>
    </div>
  );
};
