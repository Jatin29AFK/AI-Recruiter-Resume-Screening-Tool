export default function AppBrand({ onClick }) {
  const handleClick = () => {
    if (typeof onClick === 'function') {
      onClick()
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      className="group grid w-full max-w-4xl cursor-pointer grid-cols-[80px_minmax(0,1fr)] items-center gap-5 rounded-3xl bg-white px-8 py-6 text-left shadow-lg transition hover:-translate-y-0.5 hover:shadow-xl"
      title="Click to restart HireFit"
    >
      <div className="flex justify-center">
        <img
          src="/favicon.svg"
          alt="HireFit logo"
          className="h-16 w-16 rounded-2xl object-contain shrink-0"
        />
      </div>

      <div className="flex flex-col items-center justify-center text-center">
        <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl">
          HireFit
        </h1>
        <p className="mt-2 text-sm font-medium text-gray-500 group-hover:text-gray-700 sm:text-lg">
          AI-powered recruiter screening · rank candidates · shortlist with evidence
        </p>
      </div>
    </button>
  )
}