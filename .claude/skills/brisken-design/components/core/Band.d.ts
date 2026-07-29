export interface BandProps {
  children: React.ReactNode;
  /** optional second line, set regular weight at 72% opacity */
  sub?: React.ReactNode;
  tone?: 'ink' | 'teal' | 'deep' | 'quiet';
  align?: 'left' | 'center';
  style?: React.CSSProperties;
}
export declare function Band(props: BandProps): JSX.Element;
