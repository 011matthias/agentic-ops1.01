export interface SlideFooterProps {
  label?: string;
  page?: React.ReactNode;
  /** 1 = 1920 slide canvas; pass a fraction for smaller frames */
  scale?: number;
  style?: React.CSSProperties;
}
export declare function SlideFooter(props: SlideFooterProps): JSX.Element;
