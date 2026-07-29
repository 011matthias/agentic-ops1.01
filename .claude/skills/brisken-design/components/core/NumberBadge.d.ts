export interface NumberBadgeProps {
  n: React.ReactNode;
  /** px square; 43 on the 1920 slide canvas */
  size?: number;
  tone?: 'teal' | 'ink';
  style?: React.CSSProperties;
}
export declare function NumberBadge(props: NumberBadgeProps): JSX.Element;
