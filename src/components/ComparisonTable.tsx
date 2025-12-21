import { motion } from 'framer-motion';

const tableData = [
  {
    feature: "Detection Accuracy",
    phishingLens: "98.7%",
    traditional: "85-92%",
    marketLeaders: "90-95%",
  },
  {
    feature: "Multi-Modal Analysis",
    phishingLens: "Text + URL + Image",
    traditional: "URL Only",
    marketLeaders: "Text + URL",
  },
  {
    feature: "Response Time",
    phishingLens: "<500ms",
    traditional: "2-5 seconds",
    marketLeaders: "1-2 seconds",
  },
  {
    feature: "AI Models Used",
    phishingLens: "4 Advanced Models",
    traditional: "Rule-based",
    marketLeaders: "1-2 Models",
  },
  {
    feature: "Real-time Processing",
    phishingLens: "Yes",
    traditional: "Batch Processing",
    marketLeaders: "Limited",
  },
  {
    feature: "Chrome Extension",
    phishingLens: "Built-in",
    traditional: "No",
    marketLeaders: "Separate Tool",
  },
  {
    feature: "Cost Efficiency",
    phishingLens: "70% Lower",
    traditional: "High Cost",
    marketLeaders: "Premium Pricing",
  },
  {
    feature: "Deployment Time",
    phishingLens: "<1 Hour",
    traditional: "Weeks",
    marketLeaders: "Days",
  },
];

const ComparisonTable = () => {
  return (
    <div className="glass-surface overflow-hidden rounded-3xl p-8 shadow-xl">
      <div className="mb-8 text-center">
        <h3 className="text-3xl font-bold text-slate-900 dark:text-white">
          🏆 Why Choose PhishingLens?
        </h3>
        <p className="mt-3 text-slate-600 dark:text-slate-400">
          See how PhishingLens compares to traditional security solutions
        </p>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-200 dark:border-white/10">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-gradient-to-r from-slate-900 to-slate-700 text-white dark:from-slate-800 dark:to-slate-900">
              <th className="px-6 py-4 text-left font-semibold uppercase tracking-wider">
                Feature
              </th>
              <th className="px-6 py-4 text-center font-semibold uppercase tracking-wider">
                PhishingLens
              </th>
              <th className="px-6 py-4 text-center font-semibold uppercase tracking-wider">
                Market Leaders
              </th>
              <th className="px-6 py-4 text-center font-semibold uppercase tracking-wider">
                Traditional
              </th>
            </tr>
          </thead>
          <tbody>
            {tableData.map((row, index) => (
              <motion.tr
                key={index}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.05 }}
                className={`transition-colors hover:bg-slate-50 dark:hover:bg-slate-900/50 ${
                  index % 2 === 0
                    ? 'bg-slate-50/50 dark:bg-slate-950/30'
                    : 'bg-white dark:bg-slate-950/10'
                }`}
              >
                <td className="px-6 py-4 font-semibold text-slate-900 dark:text-slate-100">
                  {row.feature}
                </td>
                <td className="px-6 py-4 text-center font-semibold text-emerald-600 dark:text-emerald-400">
                  {row.phishingLens}
                </td>
                <td className="px-6 py-4 text-center text-amber-600 dark:text-amber-400">
                  {row.marketLeaders}
                </td>
                <td className="px-6 py-4 text-center text-rose-600 dark:text-rose-400">
                  {row.traditional}
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 flex items-center justify-center gap-6 text-xs font-medium uppercase tracking-wider">
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-emerald-500"></div>
          <span className="text-slate-600 dark:text-slate-400">Best Performance</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-amber-500"></div>
          <span className="text-slate-600 dark:text-slate-400">Competitive</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-3 w-3 rounded-full bg-rose-500"></div>
          <span className="text-slate-600 dark:text-slate-400">Outdated</span>
        </div>
      </div>
    </div>
  );
};

export default ComparisonTable;
