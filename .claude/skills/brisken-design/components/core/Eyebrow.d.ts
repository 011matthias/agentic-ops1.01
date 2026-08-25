/**
 * @startingPoint section="Foundations" subtitle="Tracked all-caps section label" viewport="700x150"
 */
export interface EyebrowProps {
  children: React.ReactNode;
  /** teal on light, bright on dark ink, muted for column labels like SOURCES */
  tone?: 'teal' | 'bright' | 'muted';
  /** px; 12 for web, 25 on the 1920 slide canvas */
  size?: number;
  as?: keyof JSX.IntrinsicElements;
  style?: React.CSSProperties;
}
export declare function Eyebrow(props: EyebrowProps): JSX.Element;
