/**
 * Lower Third composition - Animated lower third graphics.
 */

import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring
} from "remotion";

interface LowerThirdProps {
  name: string;
  title?: string;
  accentColor: string;
  position: "left" | "center" | "right";
}

export const LowerThird: React.FC<LowerThirdProps> = ({
  name,
  title,
  accentColor,
  position
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Slide in animation
  const slideProgress = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 100 }
  });

  const xOffset = interpolate(slideProgress, [0, 1], [-1920, 0]);

  // Position styles
  const positionStyles: Record<string, React.CSSProperties> = {
    left: {
      left: 50,
      bottom: 100,
      transform: `translateX(${xOffset}px)`
    },
    center: {
      left: "50%",
      bottom: 100,
      transform: `translateX(calc(-50% + ${xOffset}px))`
    },
    right: {
      right: 50,
      bottom: 100,
      transform: `translateX(${xOffset}px)`
    }
  };

  return (
    <AbsoluteFill>
      <div style={positionStyles[position]}>
        {/* Background */}
        <div
          style={{
            position: "absolute",
            left: -20,
            top: -20,
            width: "calc(100% + 40px)",
            height: "calc(100% + 40px)",
            backgroundColor: "rgba(0, 0, 0, 0.8)",
            borderRadius: 10,
            backdropFilter: "blur(10px)"
          }}
        />

        {/* Accent bar */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 6,
            height: "100%",
            backgroundColor: accentColor,
            borderRadius: "10px 0 0 10px"
          }}
        />

        {/* Content */}
        <div
          style={{
            position: "relative",
            padding: "20px 30px",
            color: "white",
            minWidth: 300
          }}
        >
          {title && (
            <div
              style={{
                fontSize: 24,
                fontWeight: 500,
                color: accentColor,
                marginBottom: 5,
                textTransform: "uppercase",
                letterSpacing: "1px"
              }}
            >
              {title}
            </div>
          )}
          <div
            style={{
              fontSize: 42,
              fontWeight: "bold",
              textShadow: "2px 2px 4px rgba(0,0,0,0.5)"
            }}
          >
            {name}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
