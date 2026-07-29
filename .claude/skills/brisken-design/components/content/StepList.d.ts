/**
 * @startingPoint section="Content" subtitle="Numbered teal steps, one sentence each" viewport="700x260"
 */
export interface StepListProps {
  /** one short sentence per step, each ending in a full stop */
  steps: React.ReactNode[];
  badgeSize?: number;
  gap?: number;
  tone?: 'ink' | 'onDark';
  style?: React.CSSProperties;
}
export declare function StepList(props: StepListProps): JSX.Element;
