/**
 * @startingPoint section="Foundations" subtitle="Teal primary, hairline ghost, on-dark" viewport="700x150"
 */
export interface ButtonProps {
  children: React.ReactNode;
  /** primary = solid teal · ghost = hairline outline · onDark = bright teal on ink · quiet = inline text link */
  variant?: 'primary' | 'ghost' | 'onDark' | 'quiet';
  size?: 's' | 'm' | 'l';
  href?: string;
  onClick?: React.MouseEventHandler;
  style?: React.CSSProperties;
}
export declare function Button(props: ButtonProps): JSX.Element;
