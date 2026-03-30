/**
 * Custom Transition composition - Various transition effects.
 */

import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate
} from "remotion";

interface CustomTransitionProps {
  type: "wipe" | "circle" | "zoom";
  direction?: "left" | "right" | "up" | "down";
  color: string;
}

export const CustomTransition: React.FC<CustomTransitionProps> = ({
  type,
  direction = "left",
  color
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const progress = frame / durationInFrames;

  if (type === "wipe") {
    return <WipeTransition progress={progress} direction={direction} color={color} />;
  }

  if (type === "circle") {
    return <CircleTransition progress={progress} color={color} />;
  }

  // Default zoom transition
  return <ZoomTransition progress={progress} color={color} />;
};

interface WipeProps {
  progress: number;
  direction: string;
  color: string;
}

const WipeTransition: React.FC<WipeProps> = ({ progress, direction, color }) => {
  let wipeX = 0;

  if (direction === "right") {
    wipeX = interpolate(progress, [0, 1], [0, 1920]);
  } else if (direction === "left") {
    wipeX = interpolate(progress, [0, 1], [0, 1920]);
  } else if (direction === "up") {
    wipeX = interpolate(progress, [0, 1], [0, 1080]);
  } else if (direction === "down") {
    wipeX = interpolate(progress, [0, 1], [0, 1080]);
  }

  if (direction === "right") {
    return (
      <AbsoluteFill>
        <div
          style={{
            position: "absolute",
            left: 1920 - wipeX,
            top: 0,
            width: wipeX,
            height: 1080,
            backgroundColor: color
          }}
        />
      </AbsoluteFill>
    );
  }

  if (direction === "left") {
    return (
      <AbsoluteFill>
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: wipeX,
            height: 1080,
            backgroundColor: color
          }}
        />
      </AbsoluteFill>
    );
  }

  return null;
};

interface CircleProps {
  progress: number;
  color: string;
}

const CircleTransition: React.FC<CircleProps> = ({ progress, color }) => {
  const circleSize = interpolate(progress, [0, 1], [0, 3000]);

  return (
    <AbsoluteFill style={{ backgroundColor: color }}>
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          transform: "translate(-50%, -50%)",
          width: circleSize,
          height: circleSize,
          borderRadius: "50%",
          backgroundColor: "white"
        }}
      />
    </AbsoluteFill>
  );
};

interface ZoomProps {
  progress: number;
  color: string;
}

const ZoomTransition: React.FC<ZoomProps> = ({ progress, color }) => {
  const scale = interpolate(progress, [0, 1], [0.5, 4]);
  const opacity = interpolate(progress, [0, 0.3, 0.7, 1], [0, 1, 1, 0]);

  return (
    <AbsoluteFill style={{ backgroundColor: color }}>
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          transform: `translate(-50%, -50%) scale(${scale})`,
          opacity,
          width: 200,
          height: 200,
          borderRadius: "50%",
          backgroundColor: "white"
        }}
      />
    </AbsoluteFill>
  );
};
