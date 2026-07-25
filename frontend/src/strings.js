// Every user-facing string, in Bulgarian, in one place. This is NOT i18n and
// there is no language switcher; it is a single file so the wording is easy to
// review and correct. Components import from here instead of hardcoding text.
// Room ids ("3.3", "A11"), code, comments, and console logs are not user-facing
// and stay as they are. Functions are used where a value is interpolated.

export const strings = {
  common: {
    to: 'до', // date-range connector, e.g. 10.08 до 15.08
    loading: 'Зареждане...',
    logout: 'Изход',
    cancel: 'Отказ',
  },

  // Room type as shown to the user. The value comes from the backend enum.
  roomTypes: {
    double: 'двойна',
    triple: 'тройна',
    apartment: 'апартамент',
    studio: 'студио',
  },

  tabs: {
    availability: 'Наличност',
    reservations: 'Резервации',
    planner: 'Календар',
  },

  login: {
    title: 'Резервации',
    passwordLabel: 'Парола',
    submit: 'Вход',
    submitting: 'Влизане...',
    wrongPassword: 'Грешна парола.',
    tooManyAttempts: 'Твърде много опити. Изчакайте минута и опитайте отново.',
    failed: 'Входът е неуспешен. Проверете връзката.',
  },

  search: {
    checkIn: 'Настаняване',
    checkOut: 'Напускане',
    invalidRange: 'Датата на напускане трябва да е след настаняването.',
    loadError: 'Наличността не можа да се зареди.',
    freeHeading: 'Свободни',
    bookedHeading: 'Заети',
    noneFree: 'Няма свободни стаи за тези дати.',
    freeTag: 'Свободна',
    bookedTag: 'Заета',
    sleeps: (n) => `${n} спални места`,
  },

  reservations: {
    filterAll: 'Всички',
    filterOwes: 'Дължат депозит',
    loadError: 'Резервациите не можаха да се заредят.',
    emptyAll: 'Няма резервации.',
    emptyOwes: 'Всички са платили депозит.',
    roomPrefix: 'Стая',
    depositPaid: (amount) => `Платен ${amount} €`,
    owesDeposit: 'Дължи депозит',
  },

  booking: {
    titleNew: 'Нова резервация',
    titleEdit: 'Редакция на резервация',
    guestName: 'Име на госта',
    phone: 'Телефон',
    room: 'Стая',
    pickRoom: 'Изберете стая',
    checkIn: 'Настаняване',
    checkOut: 'Напускане',
    guests: 'Гости',
    deposit: 'Депозит (€)',
    parking: 'Паркинг',
    note: 'Бележка',
    submitNew: 'Създай резервация',
    submitEdit: 'Запази промените',
    submitting: 'Запазване...',
    cancel: 'Отказ',
    deleteTrigger: 'Изтрий резервацията',
    deleteQuestion: 'Да изтрия ли тази резервация?',
    deleteYes: 'Да, изтрий',
    // Field names used inside the "please fill in ..." message.
    fields: {
      guestName: 'име на госта',
      phone: 'телефон',
      room: 'стая',
      checkIn: 'настаняване',
      checkOut: 'напускане',
      guests: 'гости',
    },
    fillIn: (fields) => `Моля, попълнете: ${fields}.`,
    invalidRange: 'Датата на напускане трябва да е след настаняването.',
    conflict: (room, guest, checkIn, checkOut) =>
      `Стая ${room} вече е заета от ${guest} (${checkIn} до ${checkOut}).`,
    conflictGeneric: 'Тези дати се застъпват с друга резервация.',
    guestsMin: 'Броят гости трябва да е поне 1.',
    depositNegative: 'Депозитът не може да е отрицателен.',
    validationGeneric: 'Моля, проверете полетата.',
    saveError: 'Запазването е неуспешно.',
    deleteError: 'Изтриването е неуспешно.',
    loadError: 'Резервацията не можа да се зареди.',
  },

  planner: {
    from: 'От',
    to: 'До',
    room: 'Стая',
    invalidRange: 'Крайната дата трябва да е след началната.',
    loadError: 'Календарът не можа да се зареди.',
    free: 'Свободна',
    booked: 'Заета',
  },
}
