/**
 * Remotion Root component - Defines all available compositions.
 */

import React from "react";
import { Composition } from "remotion";
import { Intro } from "./compositions/Intro";
import { LowerThird } from "./compositions/LowerThird";
import { CustomTransition } from "./compositions/CustomTransition";
import { DataViz } from "./compositions/DataViz";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Intro Composition */}
      <Composition
        id="Intro"
        component={Intro}
        durationInFrames={90}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          title: "Video Title",
          subtitle: "A subtitle here",
          logoPath: null,
          accentColor: "#4ecdc4"
        }}
      />

      {/* Lower Third Composition */}
      <Composition
        id="LowerThird"
        component={LowerThird}
        durationInFrames={120}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          name: "Guest Name",
          title: "Expert Title",
          accentColor: "#4ecdc4",
          position: "left" as const
        }}
      />

      {/* Custom Transition Composition */}
      <Composition
        id="CustomTransition"
        component={CustomTransition}
        durationInFrames={60}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          type: "wipe" as const,
          direction: "left" as const,
          color: "#000000"
        }}
      />

      {/* Data Visualization Composition */}
      <Composition
        id="DataViz"
        component={DataViz}
        durationInFrames={180}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          data: [
            { label: "Category A", value: 75, color: "#4ecdc4" },
            { label: "Category B", value: 50, color: "#ff6b6b" },
            { label: "Category C", value: 90, color: "#95e1d3" }
          ],
          chartType: "bar" as const,
          title: "Data Visualization"
        }}
      />
    </>
  );
};
