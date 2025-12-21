import { useEffect, useState } from 'react';
const useScrollHideNav = (offset = 32) => {
    const [isHidden, setIsHidden] = useState(false);
    const [isAtTop, setIsAtTop] = useState(true);
    useEffect(() => {
        let lastY = window.scrollY;
        const handleScroll = () => {
            const currentY = window.scrollY;
            setIsAtTop(currentY <= offset);
            if (Math.abs(currentY - lastY) < 6)
                return;
            setIsHidden(currentY > lastY && currentY > offset);
            lastY = currentY;
        };
        window.addEventListener('scroll', handleScroll, { passive: true });
        return () => window.removeEventListener('scroll', handleScroll);
    }, [offset]);
    return { isHidden, isAtTop };
};
export default useScrollHideNav;
