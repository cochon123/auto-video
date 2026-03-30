/**
 * Intro composition - Animated intro with logo and title.
 */

import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring
} from "remotion";

interface IntroProps {
  title: string;
  subtitle?: string;
  logoPath?: string | null;
  accentColor: string;
}

export const Intro: React.FC<IntroProps> = ({
  title,
  subtitle,
  logoPath,
  accentColor
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Logo animation
  const logoScale = spring({
    frame: frame - 10,
    fps,
    config: { damping: 10, stiffness: 80 }
  });

  const logoOpacity = interpolate(frame, [0, 20], [0, 1]);

  // Title animation
  const titleY = spring({
    frame: frame - 30,
    fps,
    config: { damping: 15, stiffness: 100 }
  });

  const titleOpacity = interpolate(frame, [20, 40], [0, 1]);

  // Subtitle animation
  const subtitleOpacity = interpolate(frame, [50, 70], [0, 1]);

  // Accent line animation
  const lineWidth = interpolate(frame, [40, 80], [0, 300]);
  const lineOpacity = interpolate(frame, [40, 60], [0, 1]);

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a0a" }}>
      {/* Logo placeholder */}
      {logoPath && (
        <div
          style={{
            position: "absolute",
            top: 100,
            left: "50%",
            transform: `translateX(-50%) scale(${logoScale})`,
            opacity: logoOpacity
          }}
        >
          <div
            style={{
              width: 120,
              height: 120,
              borderRadius: "50%",
              backgroundColor: accentColor,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 48,
              color: "white",
              fontWeight: "bold"
            }}
          >
            LOGO
          </div>
        </div>
      )}

      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: "40%",
          left: "50%",
          transform: `translate(-50%, ${titleY * 50}px)`,
          opacity: titleOpacity,
          textAlign: "center"
        }}
      >
        <div
          style={{
            fontSize: 72,
            fontWeight: "bold",
            color: "#ffffff",
            textShadow: "0 4px 20px rgba(0,0,0,0.5)"
          }}
        >
          {title}
        </div>
      </div>

      {/* Subtitle */}
      {subtitle && frame > 50 && (
        <div
          style={{
            position: "absolute",
            top: "55%",
            left: "50%",
            transform: "translateX(-50%)",
            opacity: subtitleOpacity,
            textAlign: "center"
          }}
        >
          <div
            style={{
              fontSize: 36,
              fontWeight: "normal",
              color: "#cccccc"
            }}
          >
            {subtitle}
          </div>
        </div>
      )}

      {/* Accent line */}
      <div
        style={{
          position: "absolute",
          bottom: 100,
          left: "50%",
          transform: "translateX(-50%)",
          width: lineWidth,
          height: 4,
          backgroundColor: accentColor,
          opacity: lineOpacity,
          borderRadius: 2
        }}
      />
    </AbsoluteFill>
  );
};
