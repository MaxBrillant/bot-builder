import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface IconBadgeProps {
  icon: LucideIcon;
  variant?: 'blue' | 'green' | 'red' | 'orange' | 'gray' | 'purple' | 'yellow';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeClasses = {
  sm: 'w-8 h-8',
  md: 'w-10 h-10',
  lg: 'w-12 h-12'
};

const iconSizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-5 h-5',
  lg: 'w-6 h-6'
};

const variantClasses = {
  blue: 'bg-muted text-muted-foreground',
  green: 'bg-success/10 text-success',
  red: 'bg-destructive/10 text-destructive',
  orange: 'bg-muted text-muted-foreground',
  gray: 'bg-muted text-muted-foreground',
  purple: 'bg-muted text-muted-foreground',
  yellow: 'bg-muted text-muted-foreground'
};

export function IconBadge({
  icon: Icon,
  variant = 'blue',
  size = 'md',
  className
}: IconBadgeProps) {
  return (
    <div
      className={cn(
        "rounded-lg flex items-center justify-center flex-shrink-0",
        sizeClasses[size],
        variantClasses[variant],
        className
      )}
    >
      <Icon className={iconSizeClasses[size]} />
    </div>
  );
}
