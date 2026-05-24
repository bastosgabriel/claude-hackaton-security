export type Week = {
  start: Date
  isoWeek: number
  isoYear: number
  key: string
}

export function startOfISOWeek(d: Date): Date {
  const date = new Date(d)
  date.setHours(0, 0, 0, 0)
  const day = date.getDay() || 7
  if (day !== 1) date.setDate(date.getDate() - (day - 1))
  return date
}

export function isoWeekParts(d: Date): { isoWeek: number; isoYear: number } {
  const target = new Date(d.valueOf())
  target.setHours(0, 0, 0, 0)
  const dayNr = (target.getDay() + 6) % 7
  target.setDate(target.getDate() - dayNr + 3)
  const firstThursday = target.valueOf()
  const isoYear = target.getFullYear()
  target.setMonth(0, 1)
  if (target.getDay() !== 4) {
    target.setMonth(0, 1 + ((4 - target.getDay() + 7) % 7))
  }
  const isoWeek = 1 + Math.ceil((firstThursday - target.valueOf()) / 604800000)
  return { isoWeek, isoYear }
}

export function buildWeeks(reference: Date, count: number): Week[] {
  const currentMonday = startOfISOWeek(reference)
  const weeks: Week[] = []
  for (let i = count - 1; i >= 0; i--) {
    const start = new Date(currentMonday)
    start.setDate(currentMonday.getDate() - i * 7)
    const { isoWeek, isoYear } = isoWeekParts(start)
    weeks.push({ start, isoWeek, isoYear, key: `${isoYear}-W${isoWeek}` })
  }
  return weeks
}

const WEEK_RANGE_FORMATTER = new Intl.DateTimeFormat("pt-BR", {
  month: "short",
  day: "numeric",
})

export function formatWeekRange(start: Date): string {
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  return WEEK_RANGE_FORMATTER.formatRange(start, end)
}
