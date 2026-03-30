/**
 * Remotion Root component - Defines all available compositions.
 */

import React from "react";
import { CalculateMetadataFunction, Composition, Folder } from "remotion";
import { Intro } from "./compositions/Intro";
import { LowerThird } from "./compositions/LowerThird";
import { CustomTransition } from "./compositions/CustomTransition";
import { DataViz } from "./compositions/DataViz";
import {
  ComparisonCard,
  ComparisonCardSchema,
  ListReveal,
  ListRevealSchema,
} from "./compositions";

type ListRevealProps = React.ComponentProps<typeof ListReveal>;
type ComparisonCardProps = React.ComponentProps<typeof ComparisonCard>;
type LooseCompositionComponent = React.ComponentType<Record<string, unknown>>;

const asLooseComposition = <T extends Record<string, unknown>>(
  component: React.ComponentType<T> | React.ComponentType<any>,
): LooseCompositionComponent => component as unknown as LooseCompositionComponent;

const calculateListRevealMetadata: CalculateMetadataFunction<ListRevealProps> = ({ props }) => ({
  durationInFrames: Math.max(90, props.items.length * 45),
});

const calculateComparisonMetadata: CalculateMetadataFunction<ComparisonCardProps> = () => ({
  durationInFrames: 120,
});

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Folder name="Motion-Design">
        <Composition
          id="Intro"
          component={asLooseComposition(Intro)}
          durationInFrames={90}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{
            title: "Video Title",
            subtitle: "A subtitle here",
            logoPath: null,
            accentColor: "#4ecdc4",
          }}
        />

        <Composition
          id="LowerThird"
          component={asLooseComposition(LowerThird)}
          durationInFrames={120}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{
            name: "Guest Name",
            title: "Expert Title",
            accentColor: "#4ecdc4",
            position: "left" as const,
          }}
        />

        <Composition
          id="CustomTransition"
          component={asLooseComposition(CustomTransition)}
          durationInFrames={60}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{
            type: "wipe" as const,
            direction: "left" as const,
            color: "#000000",
          }}
        />

        <Composition
          id="DataViz"
          component={asLooseComposition(DataViz)}
          durationInFrames={180}
          fps={30}
          width={1920}
          height={1080}
          defaultProps={{
            data: [
              { label: "Category A", value: 75, color: "#4ecdc4" },
              { label: "Category B", value: 50, color: "#ff6b6b" },
              { label: "Category C", value: 90, color: "#95e1d3" },
            ],
            chartType: "bar" as const,
            title: "Data Visualization",
          }}
        />

        <Composition
          id="ListReveal"
          component={ListReveal}
          durationInFrames={120}
          fps={30}
          width={1920}
          height={1080}
          schema={ListRevealSchema}
          calculateMetadata={calculateListRevealMetadata}
          defaultProps={{
            title: "Three Key Ideas",
            items: [
              { title: "First point", subtitle: "A short explanation" },
              { title: "Second point", subtitle: "Another explanation" },
              { title: "Third point", subtitle: "A final explanation" },
            ],
            accentColor: "#4ecdc4",
            backgroundColor: "#0f172a",
          }}
        />

        <Composition
          id="ComparisonCard"
          component={ComparisonCard}
          durationInFrames={120}
          fps={30}
          width={1920}
          height={1080}
          schema={ComparisonCardSchema}
          calculateMetadata={calculateComparisonMetadata}
          defaultProps={{
            headline: "Compare Two Approaches",
            leftTitle: "Option A",
            leftBody: "This side explains the first approach.",
            rightTitle: "Option B",
            rightBody: "This side explains the second approach.",
            accentColor: "#4ecdc4",
            backgroundColor: "#111827",
          }}
        />
      </Folder>
    </>
  );
};
