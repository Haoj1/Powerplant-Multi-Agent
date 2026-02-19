import './Pagination.css'

function Pagination({ page, pageSize, total, onPageChange }) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)

  if (totalPages <= 1) {
    return (
      <div className="pagination-wrap">
        <span className="pagination-info">
          {total === 0 ? '0 items' : `${from}–${to} of ${total}`}
        </span>
      </div>
    )
  }

  const maxVisible = 7
  let pageNumbers = []
  if (totalPages <= maxVisible) {
    pageNumbers = Array.from({ length: totalPages }, (_, i) => i + 1)
  } else {
    let start = Math.max(1, page - Math.floor(maxVisible / 2))
    let end = Math.min(totalPages, start + maxVisible - 1)
    if (end - start + 1 < maxVisible) start = Math.max(1, end - maxVisible + 1)
    pageNumbers = Array.from({ length: end - start + 1 }, (_, i) => start + i)
  }

  return (
    <div className="pagination-wrap">
      <span className="pagination-info">
        {from}–{to} of {total}
      </span>
      <div className="pagination-buttons">
        <button
          type="button"
          className="pagination-btn"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          aria-label="Previous page"
        >
          Prev
        </button>
        {pageNumbers.map((p) => (
          <button
            key={p}
            type="button"
            className={`pagination-btn ${p === page ? 'active' : ''}`}
            onClick={() => onPageChange(p)}
          >
            {p}
          </button>
        ))}
        <button
          type="button"
          className="pagination-btn"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          aria-label="Next page"
        >
          Next
        </button>
      </div>
    </div>
  )
}

export default Pagination
