export interface ChipProps {
  children: React.ReactNode;
  variant?: 'bordered' | 'accent' | 'filled' | 'dark';
  align?: 'left' | 'center';
  style?: React.CSSProperties;
}
export declare function Chip(props: ChipProps): JSX.Element;
