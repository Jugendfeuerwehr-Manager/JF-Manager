import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SafeHtml from '../SafeHtml.vue'

describe('SafeHtml', () => {
  it('removes active legacy markup, encoded URLs and application CSS', () => {
    const wrapper = mount(SafeHtml, { props: { html: `
      <script>alert(1)</script><svg onload="alert(1)"></svg>
      <a href="java&#x73;cript:alert(1)" onclick="alert(1)">Unsafe</a>
      <p style="position:fixed" id="app"><strong>Formatting</strong></p>
      <iframe src="https://example.test"></iframe><form><input name="location"></form>
    ` } })
    expect(wrapper.find('script, svg, iframe, form, input').exists()).toBe(false)
    expect(wrapper.find('[onclick], [style], [id], [href]').exists()).toBe(false)
    expect(wrapper.find('strong').text()).toBe('Formatting')
  })

  it('preserves safe links and sanitizes reactive updates', async () => {
    const wrapper = mount(SafeHtml, { props: { html: '<a href="https://example.test">Link</a>' } })
    expect(wrapper.find('a').attributes('href')).toBe('https://example.test')
    await wrapper.setProps({ html: '<a href="data:text/html,test">Changed</a>' })
    expect(wrapper.find('a').attributes('href')).toBeUndefined()
  })
})
