/**
 * @startingPoint section="Content" subtitle="Flat grey card with the teal tick" viewport="700x220"
 */
export interface TickCardProps {
  title?: React.ReactNode;
  children?: React.ReactNode;
  /** one card in a row may use 'bright' as the highlight; the rest stay 'teal' */
  accent?: 'teal' | 'bright';
  tone?: 'light' | 'dark';
  /** px padding; 35 on the 1920 slide canvas */
  pad?: number;
  style?: React.CSSProperties;
}
export declare function TickCard(props: TickCardProps): JSX.Element;
