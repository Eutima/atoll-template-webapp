document.addEventListener("alpine:init", () => {
  Alpine.data("searchableSelect", () => ({
    open: false,
    value: "",
    activeIndex: -1,

    close() {
      this.open = false;
      this.activeIndex = -1;
    },

    options() {
      return Array.from(
        this.$el.querySelectorAll('[data-role="results"] [role="option"]:not([data-loadmore])'),
      );
    },

    highlightNext() {
      this.open = true;
      const opts = this.options();
      if (!opts.length) return;
      this.activeIndex = (this.activeIndex + 1) % opts.length;
      this.applyHighlight(opts);
    },

    highlightPrevious() {
      this.open = true;
      const opts = this.options();
      if (!opts.length) return;
      this.activeIndex = (this.activeIndex - 1 + opts.length) % opts.length;
      this.applyHighlight(opts);
    },

    applyHighlight(opts) {
      opts.forEach((el, i) => el.classList.toggle("bg-indigo-100", i === this.activeIndex));
      const active = opts[this.activeIndex];
      if (active) active.scrollIntoView({ block: "nearest" });
    },

    selectHighlighted() {
      const opts = this.options();
      const target = opts[this.activeIndex] || opts[0];
      if (target) this.select(target);
    },

    select(el) {
      this.value = el.dataset.value;
      this.$el.querySelector('input[type="text"]').value = el.dataset.label;
      this.close();
    },

    onResultsSwapped() {
      this.activeIndex = -1;
    },
  }));
});
