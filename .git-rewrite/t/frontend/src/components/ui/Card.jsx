import { motion } from 'framer-motion';

export function Card({ children, className = '', hover = false, ...props }) {
  const baseClasses = 'bg-card border border-border rounded-2xl overflow-hidden';
  const hoverClasses = hover ? 'transition-all duration-200 hover:bg-card-hover hover:border-primary/50' : '';
  
  const CardComponent = (
    <div className={`${baseClasses} ${hoverClasses} ${className}`} {...props}>
      {children}
    </div>
  );
  
  if (hover) {
    return (
      <motion.div whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}>
        {CardComponent}
      </motion.div>
    );
  }
  
  return CardComponent;
}

export function CardHeader({ children, className = '' }) {
  return (
    <div className={`px-4 py-3 border-b border-border ${className}`}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className = '' }) {
  return (
    <h3 className={`text-lg font-semibold text-text-primary ${className}`}>
      {children}
    </h3>
  );
}

export function CardContent({ children, className = '' }) {
  return (
    <div className={`p-4 ${className}`}>
      {children}
    </div>
  );
}

export function CardFooter({ children, className = '' }) {
  return (
    <div className={`px-4 py-3 border-t border-border ${className}`}>
      {children}
    </div>
  );
}

export default Card;