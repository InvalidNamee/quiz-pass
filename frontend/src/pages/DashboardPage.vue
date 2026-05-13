<template>
  <section class="grid gap-5">
    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h1 class="text-2xl font-bold">首页</h1>
      <p class="mt-2 text-slate-600">从题库创建、公开浏览、练习记录这些常用入口开始。</p>
    </div>
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <RouterLink class="rounded-xl border border-slate-200 bg-white p-5 hover:border-blue-300" to="/banks/generate">
        <strong>新建题库</strong>
        <span class="mt-2 block text-sm text-slate-600">上传文档并用 AI 生成题目。</span>
      </RouterLink>
      <RouterLink class="rounded-xl border border-slate-200 bg-white p-5 hover:border-blue-300" to="/banks">
        <strong>我的题库</strong>
        <span class="mt-2 block text-sm text-slate-600">管理已创建、生成或导入的题库。</span>
      </RouterLink>
      <RouterLink class="rounded-xl border border-slate-200 bg-white p-5 hover:border-blue-300" to="/banks/public">
        <strong>公开题库</strong>
        <span class="mt-2 block text-sm text-slate-600">浏览其他用户分享的题库。</span>
      </RouterLink>
    </div>
  </section>
</template>
