export interface StatProps {
  value: React.ReactNode;
  children: React.ReactNode;
  /** attribution — required in practice; Brisken cites every figure */
  source?: string;
  tone?: 'ink' | 'onDark';
  style?: React.CSSProperties;
}
export declare function Stat(props: StatProps): JSX.Element;
