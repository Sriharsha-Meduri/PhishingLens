import { motion } from 'framer-motion';

const PerformanceChart = () => {
  // Detection Accuracy data from the comparison table
  const data = [
    { label: 'PhishingLens', value: 96, color: '#10b981' },
    { label: 'Market Leaders', value: 78, color: '#f59e0b' },
    { label: 'Traditional', value: 53, color: '#ef4444' },
  ];

  const maxValue = 100;
  const yAxisSteps = [0, 25, 50, 75, 100];

  return (
    <div className="rounded-lg border border-slate-300 bg-white p-8 dark:border-slate-700 dark:bg-slate-900">
      {/* Title */}
      <h3 className="mb-8 text-center text-lg font-semibold text-slate-900 dark:text-slate-100">
        Detection Accuracy – PhishingLens vs Competitors
      </h3>

      {/* Chart Container */}
      <div className="relative">
        {/* Y-axis label */}
        <div className="absolute -left-8 top-1/2 -translate-y-1/2 -rotate-90">
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">Accuracy (%)</span>
        </div>

        {/* Chart area */}
        <div className="ml-12">
          {/* Y-axis and grid lines */}
          <div className="relative" style={{ height: '400px' }}>
            {/* Grid lines */}
            <div className="absolute inset-0 flex flex-col justify-between">
              {yAxisSteps.reverse().map((value) => (
                <div key={value} className="flex items-center">
                  <span className="w-12 text-right text-sm text-slate-600 dark:text-slate-400">{value}</span>
                  <div className="ml-4 flex-1 border-t border-slate-300 dark:border-slate-600"></div>
                </div>
              ))}
            </div>

            {/* Bars */}
            <div className="relative ml-16 flex items-end justify-around gap-8" style={{ height: '99%' }}>
              {data.map((item, index) => (
                <div key={item.label} className="flex flex-1 flex-col items-center justify-end" style={{ height: '100%' }}>
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: `${item.value}%` }}
                    transition={{ duration: 1, delay: index * 0.2, ease: 'easeOut' }}
                    className="relative w-full max-w-[100px]"
                    style={{ backgroundColor: item.color }}
                  >
                    {/* Value label on top of bar */}
                    <div className="absolute -top-6 left-0 right-0 text-center text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {item.value}%
                    </div>
                  </motion.div>
                </div>
              ))}
            </div>
          </div>

          {/* X-axis labels */}
          <div className="ml-16 mt-4 flex justify-around gap-8">
            {data.map((item) => (
              <div key={item.label} className="flex-1 max-w-[100px] text-center text-sm font-medium text-slate-700 dark:text-slate-300">
                {item.label}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Optional insight */}
      <div className="mt-6 border-t border-slate-200 pt-4 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-400">
        PhishingLens achieves 18% higher accuracy than market leaders
      </div>
    </div>
  );
};

export default PerformanceChart;
