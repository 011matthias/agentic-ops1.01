export interface CredentialRowProps {
  /** strings, or badge images from assets/badges/ */
  items: Array<string | { src: string; alt: string; height?: number }>;
  tone?: 'light' | 'onDark';
  size?: number;
  style?: React.CSSProperties;
}
export declare function CredentialRow(props: CredentialRowProps): JSX.Element;
