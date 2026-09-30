"""Publication figures from recorded aggregate results; no fitting or data selection."""

import textwrap


def _plotting():
    import matplotlib

    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    return plt


def paired_group_figure(result, output, filename):
    plt = _plotting()
    comparisons = list(result['comparisons'])
    panels = [('All requests', result['comparisons'])]
    for name, group in result['history_groups'].items():
        panels.append((f"History: {name.replace('_', ' ')} (n={group['users']})", group['comparisons']))
    columns = 2
    rows = (len(panels) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(13, 3.9 * rows), squeeze=False, sharex=True)
    labels = ['\n'.join(textwrap.wrap(name.replace('_minus_', ' − '), 31)) for name in comparisons]
    for ax, (title, values) in zip(axes.flat, panels, strict=False):
        for index, name in enumerate(comparisons):
            stat = values.get(name, {}).get('ndcg', {})
            if 'difference' not in stat:
                continue
            value = stat['difference']
            low, high = stat.get('ci_low'), stat.get('ci_high')
            errors = [[max(0, value-low)], [max(0, high-value)]] if low is not None and high is not None else None
            ax.errorbar(value, index, xerr=errors, fmt='o', capsize=3, color='tab:blue')
        ax.axvline(0, color='black', linewidth=.8)
        ax.set(yticks=range(len(comparisons)), yticklabels=labels, title=title, xlabel='Paired NDCG@10 difference')
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=.25)
    for ax in list(axes.flat)[len(panels):]:
        ax.set_visible(False)
    fig.suptitle('Recorded paired effects by predefined history group', fontsize=13)
    fig.tight_layout()
    for extension in ('png', 'svg'):
        fig.savefig(output / f'{filename}.{extension}', dpi=180)
    plt.close(fig)


def action_allocation_figure(result, output):
    plt = _plotting()
    primary = result['primary_comparison']
    names = [name for name in ['fixed_R0', 'fixed_R1', 'fixed_R2', 'fixed_R3', 'fixed_R4',
                              *primary, primary[0].replace('learned_', 'random_', 1)] if name in result['methods']]
    names.extend(name for name, row in result['methods'].items()
                 if name.startswith(('learned_', 'rule_', 'random_')) and row['mean_llm_calls'] > 0)
    names = list(dict.fromkeys(names))
    plans = list(result['methods'][names[0]]['action_counts'])
    fig, ax = plt.subplots(figsize=(max(9, .75 * len(names) + 2), 5.2))
    bottom = [0.0] * len(names)
    colors = ['#8c8c8c', '#0072b2', '#009e73', '#e69f00', '#d55e00']
    for plan, color in zip(plans, colors[:len(plans)], strict=True):
        fractions = [result['methods'][name]['action_counts'][plan] / result['methods'][name]['requests'] for name in names]
        ax.bar(range(len(names)), fractions, bottom=bottom, label=plan, color=color)
        bottom = [a+b for a, b in zip(bottom, fractions, strict=True)]
    ax.set(xticks=range(len(names)), xticklabels=[n.replace('fixed_', '').replace('_', '\n') for n in names],
           ylim=(0, 1), ylabel='Fraction of all requests', title='Selected policies: actual evidence-plan allocation')
    ax.legend(title='Plan', loc='upper left', bbox_to_anchor=(1.01, 1.0))
    fig.tight_layout()
    for extension in ('png', 'svg'):
        fig.savefig(output / f'policy_action_allocation.{extension}', dpi=180)
    plt.close(fig)
