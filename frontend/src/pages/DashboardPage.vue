<template>
  <section>
    <h1 class="text-2xl font-bold">概览</h1>
    <div class="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-blue-300" to="/banks">管理题库</RouterLink>
      <RouterLink class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-blue-300" to="/banks/public">浏览公开题库</RouterLink>
      <RouterLink class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm hover:border-blue-300" to="/banks/generate">上传文档生成题库</RouterLink>
    </div>
  </section>
</template>
