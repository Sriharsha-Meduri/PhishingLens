import { PropsWithChildren } from 'react';
import { motion, useReducedMotion } from 'framer-motion';

type ScrollFadeProps = PropsWithChildren<{ delay?: number; className?: string }>;

const ScrollFade = ({ children, delay = 0, className }: ScrollFadeProps) => {
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay }}
      viewport={{ once: true, amount: 0.3 }}
    >
      {children}
    </motion.div>
  );
};

export default ScrollFade;
