import type { DetailedHTMLProps, HTMLAttributes } from "react";

declare namespace JSX {
  interface IntrinsicElements {
    "model-viewer": DetailedHTMLProps<HTMLAttributes<HTMLElement>, HTMLElement> & {
      src?: string;
      "camera-controls"?: boolean;
      "auto-rotate"?: boolean;
      exposure?: string | number;
      "shadow-intensity"?: string | number;
    };
  }
}
