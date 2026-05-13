export const ROLES = {
  admin:             'admin',
  omts:              'omts',
  workshop_afs:      'workshop_afs',
  workshop_gls:      'workshop_gls',
  quality:           'quality',
  quality_assurance: 'quality_assurance',
  planning:          'planning',
}

export const ROLE_LABELS = {
  admin:             'Администратор',
  omts:              'ОМТС',
  workshop_afs:      'Цех АФС',
  workshop_gls:      'Цех ГЛС',
  quality:           'ОКК',
  quality_assurance: 'ООК',
  planning:          'Планово-экономический отдел',
}

export const DEPARTMENTS = [
  { value: 'workshop_afs', label: 'Цех АФС' },
  { value: 'workshop_gls', label: 'Цех ГЛС' },
  { value: 'quality',      label: 'ОКК' },
  { value: 'quality_assurance', label: 'ООК' },
  { value: 'omts',         label: 'ОМТС' },
  { value: 'planning',     label: 'Планово-экономический отдел' },
  { value: 'admin',        label: 'Администрация' },
]

export const EXPENSE_TYPE_LABELS = {
  requirement: 'Требование-накладная',
  sampling:    'Отбор проб',
  writeoff:    'Списание',
}

export const REQUEST_STATUS_LABELS = {
  pending:  'На рассмотрении',
  approved: 'Утверждена',
  rejected: 'Отклонена',
}

export const REQUEST_STATUS_COLORS = {
  pending:  'blue',
  approved: 'green',
  rejected: 'red',
}

export const SUPPLY_STATUS_LABELS = {
  draft:     'Черновик',
  confirmed: 'Подтверждена',
}

export const SUPPLY_STATUS_COLORS = {
  draft:     'orange',
  confirmed: 'green',
}

export const OPERATION_LABELS = {
  supply:      'Приход',
  requirement: 'Выдача',
  sampling:    'Отбор проб',
  writeoff:    'Списание',
}

export const OPERATION_COLORS = {
  supply:      'green',
  requirement: 'blue',
  sampling:    'purple',
  writeoff:    'orange',
}
