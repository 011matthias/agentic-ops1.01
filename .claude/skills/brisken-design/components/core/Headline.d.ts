export interface HeadlineProps {
  children: React.ReactNode;
  /** named step, or a raw px number for slide-scale type */
  size?: 'xl' | 'l' | 'm' | 's' | number;
  tone?: 'ink' | 'onDark';
  as?: keyof JSX.IntrinsicElements;
  style?: React.CSSProperties;
}
export declare function Headline(props: HeadlineProps): JSX.Element;
