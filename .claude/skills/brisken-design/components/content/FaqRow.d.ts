export interface FaqRowProps {
  /** phrased as the question a customer would actually type */
  question: React.ReactNode;
  children?: React.ReactNode;
  open?: boolean;
  onToggle?: React.MouseEventHandler;
  style?: React.CSSProperties;
}
export declare function FaqRow(props: FaqRowProps): JSX.Element;
