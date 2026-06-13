import { DataGrid, GridColDef, GridRowsProp } from '@mui/x-data-grid';

export default function CustomizedDataGrid({
  rows,
  columns,
  loading,
}: {
  rows: GridRowsProp;
  columns: GridColDef[];
  loading?: boolean;
}) {
  return (
    <DataGrid
      checkboxSelection
      rows={rows}
      columns={columns}
      getRowClassName={(params) =>
        params.indexRelativeToCurrentPage % 2 === 0 ? 'even' : 'odd'
      }
      loading={loading}
      initialState={{
        pagination: { paginationModel: { pageSize: 20 } },
      }}
      pageSizeOptions={[10, 20, 50]}
      disableColumnResize
      density="compact"
      slotProps={{
        filterPanel: {
          filterFormProps: {
            logicOperatorInputProps: { variant: 'outlined', size: 'small' },
            columnInputProps: { variant: 'outlined', size: 'small', sx: { mt: 'auto' } },
            operatorInputProps: { variant: 'outlined', size: 'small', sx: { mt: 'auto' } },
            valueInputProps: {
              InputComponentProps: { variant: 'outlined', size: 'small' },
            },
          },
        },
      }}
    />
  );
}
