import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { SparkLineChart } from '@mui/x-charts/SparkLineChart';
import { useTheme } from '@mui/material/styles';

export type StatCardProps = {
  title: string;
  value: string;
  interval: string;
  trend: 'up' | 'down' | 'neutral';
  data: number[];
};

export default function StatCard({ title, value, interval, trend, data }: StatCardProps) {
  const theme = useTheme();

  const trendColors: Record<string, string> = {
    up: theme.palette.mode === 'light' ? theme.palette.success.main : theme.palette.success.dark,
    down: theme.palette.mode === 'light' ? theme.palette.error.main : theme.palette.error.dark,
    neutral: theme.palette.mode === 'light' ? theme.palette.grey[400] : theme.palette.grey[700],
  };

  const labelColors: Record<string, 'success' | 'error' | 'default'> = {
    up: 'success',
    down: 'error',
    neutral: 'default',
  };

  const trendValues: Record<string, string> = {
    up: '+25%',
    down: '-25%',
    neutral: '+5%',
  };

  const chartColor = trendColors[trend];
  const color = labelColors[trend];

  return (
    <Card variant="outlined" sx={{ height: '100%', flexGrow: 1 }}>
      <CardContent>
        <Typography component="h2" variant="subtitle2" gutterBottom>
          {title}
        </Typography>
        <Stack direction="column" justifyContent="space-between" sx={{ flexGrow: 1 }} gap={1}>
          <Stack justifyContent="space-between">
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="h4" component="p">
                {value}
              </Typography>
              <Chip size="small" color={color} label={trendValues[trend]} />
            </Stack>
            <Typography variant="caption" sx={{ color: 'text.secondary' }}>
              {interval}
            </Typography>
          </Stack>
          <Box sx={{ width: '100%', height: 50 }}>
            <SparkLineChart
              data={data}
              area
              showHighlight
              showTooltip
              xAxis={{ scaleType: 'band', data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] }}
              color={chartColor}
            />
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}
