/**
 * Remotion configuration for auto-video.
 */

import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setLogLevel("info");

// Default codec settings
Config.setCodec({
  codec: "h264",
  crf: 18,
  preset: "slow"
});

// Output settings
Config.setPixelFormat("yuv420p");
