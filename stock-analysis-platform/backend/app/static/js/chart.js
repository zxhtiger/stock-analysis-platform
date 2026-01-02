// backend/app/static/js/chart.js
/**
 * 图表工具函数
 */

// 格式化数字
function formatNumber(num) {
    if (num >= 100000000) {
        return (num / 100000000).toFixed(2) + '亿';
    } else if (num >= 10000) {
        return (num / 10000).toFixed(2) + '万';
    }
    return num.toFixed(2);
}

// 格式化百分比
function formatPercent(num) {
    return num.toFixed(2) + '%';
}

// 创建颜色渐变
function createColorGradient(startColor, endColor, steps) {
    const start = hexToRgb(startColor);
    const end = hexToRgb(endColor);
    const colors = [];

    for (let i = 0; i < steps; i++) {
        const ratio = i / (steps - 1);
        const r = Math.round(start.r + (end.r - start.r) * ratio);
        const g = Math.round(start.g + (end.g - start.g) * ratio);
        const b = Math.round(start.b + (end.b - start.b) * ratio);
        colors.push(rgbToHex(r, g, b));
    }

    return colors;
}

// 十六进制转RGB
function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

// RGB转十六进制
function rgbToHex(r, g, b) {
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

// 创建K线图选项
function createKLineOption(dates, data, title = '') {
    return {
        title: {
            text: title,
            left: 'center'
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            }
        },
        legend: {
            data: ['日K', 'MA5', 'MA10', 'MA20'],
            top: 30
        },
        grid: {
            left: '10%',
            right: '10%',
            bottom: '15%'
        },
        xAxis: {
            type: 'category',
            data: dates,
            boundaryGap: false,
            axisLine: { onZero: false },
            splitLine: { show: false },
            min: 'dataMin',
            max: 'dataMax',
            axisLabel: {
                rotate: 45
            }
        },
        yAxis: {
            scale: true,
            splitArea: {
                show: true
            }
        },
        dataZoom: [
            {
                type: 'inside',
                start: 50,
                end: 100
            },
            {
                show: true,
                type: 'slider',
                top: '90%',
                start: 50,
                end: 100
            }
        ],
        series: [
            {
                name: '日K',
                type: 'candlestick',
                data: data,
                itemStyle: {
                    color: '#ec0000',
                    color0: '#00da3c',
                    borderColor: '#8A0000',
                    borderColor0: '#008F28'
                }
            }
        ]
    };
}

// 创建资金流向图选项
function createCapitalFlowOption(dates, netInflows, inflowRatios) {
    return {
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            }
        },
        legend: {
            data: ['净流入', '流入比例']
        },
        grid: [
            {
                left: '10%',
                right: '10%',
                top: '10%',
                height: '60%'
            },
            {
                left: '10%',
                right: '10%',
                top: '75%',
                height: '15%'
            }
        ],
        xAxis: [
            {
                type: 'category',
                data: dates,
                gridIndex: 0,
                axisLabel: {
                    rotate: 45
                }
            },
            {
                type: 'category',
                data: dates,
                gridIndex: 1,
                show: false
            }
        ],
        yAxis: [
            {
                type: 'value',
                gridIndex: 0,
                name: '净流入(万)'
            },
            {
                type: 'value',
                gridIndex: 1,
                name: '比例(%)'
            }
        ],
        series: [
            {
                name: '净流入',
                type: 'bar',
                xAxisIndex: 0,
                yAxisIndex: 0,
                data: netInflows.map(v => v / 10000),
                itemStyle: {
                    color: function(params) {
                        return params.value > 0 ? '#28a745' : '#dc3545';
                    }
                }
            },
            {
                name: '流入比例',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: inflowRatios,
                smooth: true,
                lineStyle: {
                    width: 2
                },
                itemStyle: {
                    color: '#007bff'
                }
            }
        ]
    };
}

// 创建热力图选项
function createHeatmapOption(data, title = '') {
    return {
        title: {
            text: title,
            left: 'center'
        },
        tooltip: {
            position: 'top'
        },
        grid: {
            height: '50%',
            top: '10%'
        },
        xAxis: {
            type: 'category',
            data: data.xAxis,
            splitArea: {
                show: true
            }
        },
        yAxis: {
            type: 'category',
            data: data.yAxis,
            splitArea: {
                show: true
            }
        },
        visualMap: {
            min: data.min,
            max: data.max,
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: '15%'
        },
        series: [{
            name: '热度',
            type: 'heatmap',
            data: data.values,
            label: {
                show: true
            },
            emphasis: {
                itemStyle: {
                    shadowBlur: 10,
                    shadowColor: 'rgba(0, 0, 0, 0.5)'
                }
            }
        }]
    };
}

// 创建雷达图选项
function createRadarOption(indicators, values, title = '') {
    return {
        title: {
            text: title,
            left: 'center'
        },
        radar: {
            indicator: indicators
        },
        series: [{
            type: 'radar',
            data: [{
                value: values,
                name: '评分'
            }],
            areaStyle: {
                color: 'rgba(0, 123, 255, 0.3)'
            },
            lineStyle: {
                width: 2
            },
            itemStyle: {
                color: '#007bff'
            }
        }]
    };
}

// 导出函数供全局使用
window.chartUtils = {
    formatNumber,
    formatPercent,
    createColorGradient,
    createKLineOption,
    createCapitalFlowOption,
    createHeatmapOption,
    createRadarOption
};