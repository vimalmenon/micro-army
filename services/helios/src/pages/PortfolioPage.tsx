import { usePortfolio } from '../hooks/usePortfolio';

import { DataGrid, GridColDef } from '@mui/x-data-grid';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
  }).format(value);
}

function formatPct(value: number): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

// Numeric columns: right-align the cells *and* the headers so digits line up
// under each other. Without headerAlign the header stays left while the data
// is pulled right by type:'number', which is what looked misaligned.
const numCol = { align: 'right', headerAlign: 'right' } as const;

const columns: GridColDef[] = [
  {
    field: 'ticker',
    headerName: 'Ticker',
    width: 100,
    renderCell: (params) => (
      <Typography fontWeight={600}>{params.value}</Typography>
    ),
  },
  { field: 'name', headerName: 'Company', width: 220 },
  {
    field: 'shares',
    headerName: 'Qty',
    width: 100,
    ...numCol,
    renderCell: (params) => (
      <Typography component="span" sx={{ fontVariantNumeric: 'tabular-nums' }}>
        {params.row.shares.toLocaleString()}
        {params.row.unit && params.row.unit !== 'shares' ? ` ${params.row.unit}` : ''}
      </Typography>
    ),
  },
  {
    field: 'price',
    headerName: 'Price',
    width: 120,
    type: 'number',
    ...numCol,
    valueFormatter: (value: number) => formatCurrency(value),
  },
  {
    // Only holdings with a known purchase price show a cost; the rest render an
    // em dash rather than a fabricated basis.
    field: 'cost_basis',
    headerName: 'Cost',
    width: 105,
    ...numCol,
    valueFormatter: (value: number | null) =>
      value === null || value === undefined ? '—' : formatCurrency(value),
  },
  {
    // What the position actually cost — cost basis × quantity, as opposed to
    // what it is worth now.
    field: 'cost_value',
    headerName: 'Invested',
    width: 125,
    ...numCol,
    valueFormatter: (value: number | null) =>
      value === null || value === undefined ? '—' : formatCurrency(value),
  },
  {
    field: 'change_pct',
    headerName: 'Change %',
    width: 110,
    ...numCol,
    renderCell: (params) => {
      const val = params.value as number;
      return (
        <Typography color={val >= 0 ? 'success.main' : 'error.main'}>
          {formatPct(val)}
        </Typography>
      );
    },
  },
  {
    field: 'change_dollar',
    headerName: 'Change €',
    width: 120,
    ...numCol,
    renderCell: (params) => {
      const val = params.value as number;
      return (
        <Typography color={val >= 0 ? 'success.main' : 'error.main'}>
          {formatCurrency(val)}
        </Typography>
      );
    },
  },
  {
    field: 'total_value',
    headerName: 'Total Value',
    width: 140,
    type: 'number',
    ...numCol,
    valueFormatter: (value: number) => formatCurrency(value),
  },
  {
    field: 'total_pnl',
    headerName: 'P&L',
    width: 120,
    ...numCol,
    renderCell: (params) => {
      const val = params.value as number;
      return (
        <Typography color={val >= 0 ? 'success.main' : 'error.main'} fontWeight={600}>
          {formatCurrency(val)}
        </Typography>
      );
    },
  },
  {
    // Gain since purchase. Rendered as "+23.96% (+€11,289.82)"; blank where no
    // cost basis exists.
    field: 'total_return_pct',
    headerName: 'Return',
    width: 175,
    ...numCol,
    renderCell: (params) => {
      const pct = params.row.total_return_pct;
      if (pct === null || pct === undefined) {
        return <Typography color="text.disabled">—</Typography>;
      }
      const abs = params.row.total_return ?? 0;
      return (
        <Typography
          color={pct >= 0 ? 'success.main' : 'error.main'}
          fontWeight={600}
          sx={{ fontVariantNumeric: 'tabular-nums' }}
        >
          {formatPct(pct)}{' '}
          <Box component="span" sx={{ fontWeight: 400, opacity: 0.75 }}>
            ({formatCurrency(abs)})
          </Box>
        </Typography>
      );
    },
  },
];

export function PortfolioPage() {
  const { data, loading, error, refresh } = usePortfolio();

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Portfolio
      </Typography>

      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}

      {/* Summary cards */}
      {data && (
        <Stack direction="row" spacing={3} sx={{ mb: 3 }}>
          <Card sx={{ minWidth: 200 }}>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                Total Value
              </Typography>
              <Typography variant="h5">{formatCurrency(data.total_value)}</Typography>
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200 }}>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                Today's P&L
              </Typography>
              <Typography
                variant="h5"
                color={data.total_pnl >= 0 ? 'success.main' : 'error.main'}
              >
                {formatCurrency(data.total_pnl)}
              </Typography>
            </CardContent>
          </Card>
          <Card sx={{ minWidth: 200 }}>
            <CardContent>
              <Typography variant="overline" color="text.secondary">
                Market
              </Typography>
              <Typography variant="h5">
                {data.market_open === null
                  ? '—'
                  : data.market_open
                    ? '🟢 Open'
                    : '🔴 Closed'}
              </Typography>
            </CardContent>
          </Card>
        </Stack>
      )}

      {/* Table */}
      <Card>
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="subtitle2" color="text.secondary">
            {data ? `Updated ${new Date(data.updated_at).toLocaleTimeString()}` : 'Loading…'}
          </Typography>
          <Button
            size="small"
            startIcon={<RefreshRoundedIcon />}
            onClick={refresh}
            disabled={loading}
          >
            Refresh
          </Button>
        </Box>
        <DataGrid
          rows={data?.holdings ?? []}
          columns={columns}
          getRowId={(row) => row.ticker}
          loading={loading}
          autoHeight
          disableRowSelectionOnClick
          sx={{
            border: 'none',
            // Tabular figures: equal-width digits, so decimal points stack in a
            // straight column instead of drifting with proportional numerals.
            '& .MuiDataGrid-cell, & .MuiDataGrid-columnHeaderTitle': {
              fontVariantNumeric: 'tabular-nums',
            },
          }}
        />
      </Card>
    </Box>
  );
}
