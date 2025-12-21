import { jsx as _jsx } from "react/jsx-runtime";
import { motion, useReducedMotion } from 'framer-motion';
const ScrollFade = ({ children, delay = 0, className }) => {
    const prefersReducedMotion = useReducedMotion();
    if (prefersReducedMotion) {
        return _jsx("div", { className: className, children: children });
    }
    return (_jsx(motion.div, { className: className, initial: { opacity: 0, y: 16 }, whileInView: { opacity: 1, y: 0 }, transition: { duration: 0.6, delay }, viewport: { once: true, amount: 0.3 }, children: children }));
};
export default ScrollFade;
