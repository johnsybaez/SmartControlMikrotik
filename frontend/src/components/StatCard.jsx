export default function StatCard({ stat }) {
  const Icon = stat.icon;
  
  return (
    <div className="bg-[#121212] border border-[#232323] rounded-lg p-6 hover:border-[#e00000] transition-colors shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className={`${stat.color} bg-opacity-20 p-3 rounded-lg`}>
          <Icon className={`w-6 h-6 ${stat.color.replace('bg-', 'text-')}`} />
        </div>
        <span className={`text-sm font-medium ${
          stat.trend.startsWith('+') ? 'text-green-500' : 'text-red-500'
        }`}>
          {stat.trend}
        </span>
      </div>
      <h3 className="text-gray-400 text-sm font-medium mb-1">{stat.title}</h3>
      <p className="text-white text-2xl font-bold">{stat.value}</p>
    </div>
  );
}
