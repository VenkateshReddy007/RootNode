import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { CalendarDays } from 'lucide-react';

/* ── Parse "4-5 days" → take the max number ── */
function parseDays(str) {
  if (!str) return 2;
  const nums = str.match(/\d+/g);
  if (!nums) return 2;
  return Math.max(...nums.map(Number));
}

/* ── Build chart data ── */
function buildGanttData(waves, timeline) {
  const data = [];
  let waveStart = 0;

  waves.forEach((apps) => {
    let maxDuration = 0;

    apps.forEach((app) => {
      const duration = parseDays(timeline[app]);
      maxDuration = Math.max(maxDuration, duration);

      data.push({
        app,
        offset: waveStart,
        duration,
        total: waveStart + duration,
      });
    });

    waveStart += maxDuration;
  });

  return data;
}

/* ── Custom Tooltip ── */
const GanttTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const { app, offset, duration } = payload[0]?.payload || {};

  return (
    <div className="bg-[#111] border border-brand-border rounded-lg px-4 py-3 shadow-xl text-sm">
      <p className="text-white font-bold mb-1">{app}</p>
      <p className="text-gray-400">
        Start:&nbsp;
        <span className="text-brand-orange font-semibold">Day {offset}</span>
      </p>
      <p className="text-gray-400">
        Duration:&nbsp;
        <span className="text-brand-orange font-semibold">{duration} days</span>
      </p>
    </div>
  );
};

/* ── Component ── */
const GanttChart = ({ waves, timeline }) => {
  const data = useMemo(
    () => buildGanttData(waves || [], timeline || {}),
    [waves, timeline]
  );

  if (!waves || waves.length === 0) return null;

  const maxDay = Math.max(...data.map((d) => d.total), 15);

  return (
    <div className="bg-brand-card border border-brand-border rounded-xl p-6 shadow-2xl">
      {/* Title */}
      <div className="flex items-center gap-2.5 mb-5">
        <CalendarDays className="w-5 h-5 text-brand-orange" />
        <h2 className="text-white text-xl font-bold tracking-wide">
          Migration Timeline
        </h2>
      </div>

      {/* Chart */}
      <div className="w-full h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 8, right: 30, bottom: 8, left: 10 }}
            barCategoryGap="28%"
          >
            <CartesianGrid
              horizontal={false}
              stroke="#2A2A2A"
              strokeDasharray="3 3"
            />

            <XAxis
              type="number"
              domain={[0, maxDay]}
              tick={{ fill: '#777', fontSize: 12 }}
              axisLine={{ stroke: '#2A2A2A' }}
              tickLine={{ stroke: '#2A2A2A' }}
              label={{
                value: 'Days',
                position: 'insideBottomRight',
                offset: -4,
                fill: '#555',
                fontSize: 12,
              }}
            />

            <YAxis
              type="category"
              dataKey="app"
              tick={{ fill: '#ccc', fontSize: 13, fontWeight: 600 }}
              axisLine={false}
              tickLine={false}
              width={60}
            />

            <Tooltip
              content={<GanttTooltip />}
              cursor={{ fill: 'rgba(255,153,0,0.04)' }}
            />

            {/* Invisible offset bar */}
            <Bar dataKey="offset" stackId="gantt" fill="transparent" radius={0} />

            {/* Visible duration bar */}
            <Bar dataKey="duration" stackId="gantt" radius={[0, 6, 6, 0]}>
              {data.map((entry, index) => (
                <Cell
                  key={index}
                  fill="#FF9900"
                  style={{ filter: 'drop-shadow(0 0 6px rgba(255,153,0,0.35))' }}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default GanttChart;
