window.layout = function () {
  return {
    sidebarOpen: false,
    sidebarMini: false,
    navbarOpen: false,
    notificationsOpen: false,
    profileMenuOpen: false,
    toggleSidebar() {
      this.sidebarOpen = !this.sidebarOpen;
    },
    toggleMini() {
      this.sidebarMini = !this.sidebarMini;
    },
    toggleNavbar() {
      this.navbarOpen = !this.navbarOpen;
    },
  };
};

window.collapse = function (open = false) {
  return {
    open,
    toggle() {
      this.open = !this.open;
    },
  };
};

// Vector map initialization
window.initVectorMap = function () {
  var mapElement = document.getElementById('worldMap');
  if (!mapElement) return;

  // Check if jsVectorMap is available
  if (typeof window.jsVectorMap === 'undefined') {
    return;
  }

  try {
    new window.jsVectorMap({
      selector: '#worldMap',
      map: 'world',
      zoomOnScroll: false,
      zoomButtons: false,
      regionStyle: {
        initial: {
          fill: '#e4e4e4',
          fillOpacity: 0.9,
          stroke: 'none',
          strokeWidth: 0,
          strokeOpacity: 0
        },
        hover: {
          fillOpacity: 0.8,
          cursor: 'pointer'
        },
        selected: {
          fill: '#666666'
        }
      },
      series: {
        regions: [{
          values: {
            US: 2920,
            DE: 1300,
            AU: 760,
            GB: 690,
            RO: 600,
            BR: 550,
            CA: 120,
            FR: 540,
            IN: 200,
            RU: 300
          },
          scale: ['#AAAAAA', '#444444'],
          normalizeFunction: 'polynomial'
        }]
      },
      onRegionTooltipShow: function (event, tooltip, code) {
        var values = {
          US: '2,920',
          DE: '1,300',
          AU: '760',
          GB: '690',
          RO: '600',
          BR: '550'
        };
        if (values[code]) {
          tooltip.text(tooltip.text() + ': ' + values[code] + ' sales');
        }
      }
    });
  } catch (e) {
    // Vector map initialization failed silently
  }
};

// Dashboard charts initialization
window.initDashboardCharts = function () {
  if (typeof Chart === 'undefined') return;

  // Register plugin for center text in donut charts
  Chart.register({
    id: 'centerText',
    beforeDraw: function (chart) {
      if (chart.config.options.elements && chart.config.options.elements.center) {
        var ctx = chart.ctx;
        var centerConfig = chart.config.options.elements.center;
        var fontStyle = centerConfig.fontStyle || 'Arial';
        var txt = centerConfig.text;
        var color = centerConfig.color || '#000';
        var sidePadding = centerConfig.sidePadding || 20;
        var sidePaddingCalculated = (sidePadding / 100) * (chart._metasets[0].data[0].innerRadius * 2);
        ctx.font = "30px " + fontStyle;
        var stringWidth = ctx.measureText(txt).width;
        var elementWidth = (chart._metasets[0].data[0].innerRadius * 2) - sidePaddingCalculated;
        var widthRatio = elementWidth / stringWidth;
        var newFontSize = Math.floor(30 * widthRatio);
        var elementHeight = (chart._metasets[0].data[0].innerRadius * 2);
        var fontSizeToUse = Math.min(newFontSize, elementHeight);
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        var centerX = ((chart.chartArea.left + chart.chartArea.right) / 2);
        var centerY = ((chart.chartArea.top + chart.chartArea.bottom) / 2);
        ctx.font = fontSizeToUse + "px " + fontStyle;
        ctx.fillStyle = color;
        ctx.fillText(txt, centerX, centerY);
      }
    }
  });

  // Chart 1: Active Users (Line chart - Total Earnings)
  var ctx = document.getElementById('activeUsers');
  if (ctx) {
    new Chart(ctx.getContext("2d"), {
      type: 'line',
      data: {
        labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"],
        datasets: [{
          label: "Active Users",
          borderColor: "#6bd098",
          pointRadius: 0,
          pointHoverRadius: 0,
          fill: false,
          borderWidth: 3,
          data: [542, 480, 430, 550, 530, 453, 380, 434, 568, 610]
        }]
      },
      options: {
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        scales: {
          y: {
            ticks: {
              color: "#9f9f9f",
              maxTicksLimit: 5,
            },
            grid: {
              drawBorder: false,
              color: 'rgba(255,255,255,0.05)'
            }
          },
          x: {
            grid: {
              drawBorder: false,
              display: false,
            },
            ticks: {
              padding: 20,
              color: "#9f9f9f"
            }
          }
        }
      }
    });
  }

  // Chart 2: Emails Campaign Chart (Line chart - Subscriptions)
  ctx = document.getElementById('emailsCampaignChart');
  if (ctx) {
    new Chart(ctx.getContext("2d"), {
      type: 'line',
      data: {
        labels: ["12pm", "3pm", "6pm", "9pm", "12am", "3am", "6am", "9am"],
        datasets: [{
          label: "Email Stats",
          borderColor: "#ef8156",
          pointHoverRadius: 0,
          pointRadius: 0,
          fill: false,
          borderWidth: 3,
          data: [40, 500, 650, 700, 1200, 1250, 1300, 1900]
        }]
      },
      options: {
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        scales: {
          y: {
            ticks: {
              color: "#9f9f9f",
              maxTicksLimit: 5,
            },
            grid: {
              drawBorder: false,
              color: 'rgba(255,255,255,0.05)'
            }
          },
          x: {
            grid: {
              drawBorder: false,
              display: false,
            },
            ticks: {
              padding: 20,
              color: "#9f9f9f"
            }
          }
        }
      }
    });
  }

  // Chart 3: Active Countries (Line chart - Downloads)
  ctx = document.getElementById('activeCountries');
  if (ctx) {
    new Chart(ctx.getContext("2d"), {
      type: 'line',
      data: {
        labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct"],
        datasets: [{
          label: "Active Countries",
          borderColor: "#fbc658",
          pointHoverRadius: 0,
          pointRadius: 0,
          fill: false,
          borderWidth: 3,
          data: [80, 78, 86, 96, 83, 85, 76, 75, 88, 90]
        }]
      },
      options: {
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        scales: {
          y: {
            ticks: {
              color: "#9f9f9f",
              maxTicksLimit: 5,
            },
            grid: {
              drawBorder: false,
              color: 'rgba(255,255,255,0.05)'
            }
          },
          x: {
            grid: {
              drawBorder: false,
              display: false,
            },
            ticks: {
              padding: 20,
              color: "#9f9f9f"
            }
          }
        }
      }
    });
  }

  // Chart 4: Activity Chart (Bar chart - 2018 Sales)
  ctx = document.getElementById('chartActivity');
  if (ctx) {
    new Chart(ctx.getContext("2d"), {
      type: 'bar',
      data: {
        labels: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
        datasets: [
          {
            label: "Tesla Model S",
            borderColor: '#fcc468',
            fill: true,
            backgroundColor: '#fcc468',
            hoverBorderColor: '#fcc468',
            borderWidth: 8,
            data: [100, 120, 80, 100, 90, 130, 110, 100, 80, 110, 130, 140, 130, 120, 130, 80, 100, 90, 120, 130],
          },
          {
            label: "BMW 5 Series",
            borderColor: '#4cbdd7',
            fill: true,
            backgroundColor: '#4cbdd7',
            hoverBorderColor: '#4cbdd7',
            borderWidth: 8,
            data: [80, 140, 50, 120, 50, 150, 60, 130, 50, 130, 150, 100, 110, 80, 140, 50, 140, 50, 110, 150],
          }
        ]
      },
      options: {
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: "rgba(0,0,0,0.5)",
            titleFont: { family: "'Helvetica Neue', 'Helvetica', 'Arial', sans-serif", size: 14, weight: 'bold' },
            bodyFont: { family: "'Helvetica Neue', 'Helvetica', 'Arial', sans-serif", size: 14 },
            padding: 6,
            cornerRadius: 6,
          }
        },
        scales: {
          y: {
            ticks: {
              color: "#9f9f9f",
              font: { weight: 'bold' },
              maxTicksLimit: 5,
              padding: 20
            },
            grid: {
              drawBorder: false,
              color: '#9f9f9f',
            }
          },
          x: {
            barPercentage: 0.4,
            grid: {
              display: false,
              drawBorder: false,
            },
            ticks: {
              padding: 20,
              color: "#9f9f9f",
              font: { weight: 'bold' }
            }
          }
        }
      }
    });
  }

  // Chart 5: Donut Chart 1 (Email Statistics - 60%)
  ctx = document.getElementById('chartDonut1');
  if (ctx) {
    new Chart(ctx.getContext("2d"), {
      type: 'doughnut',
      data: {
        labels: ['Open', 'Other'],
        datasets: [{
          label: "Emails",
          backgroundColor: ['#4acccd', '#f4f3ef'],
          borderWidth: 0,
          data: [60, 40]
        }]
      },
      options: {
        cutout: '90%',
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        elements: {
          center: {
            text: '60%',
            color: '#66615c',
            fontStyle: 'Arial',
            sidePadding: 60
          }
        }
      }
    });
  }

  // Chart 6: Donut Chart 2 (New Visitors - 34%)
  ctx = document.getElementById('chartDonut2');
  if (ctx) {
    new Chart(ctx.getContext("2d"), {
      type: 'doughnut',
      data: {
        labels: ['Visited', 'Other'],
        datasets: [{
          label: "Visitors",
          backgroundColor: ['#fcc468', '#f4f3ef'],
          borderWidth: 0,
          data: [34, 66]
        }]
      },
      options: {
        cutout: '90%',
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        elements: {
          center: {
            text: '34%',
            color: '#66615c',
            fontStyle: 'Arial',
            sidePadding: 60
          }
        }
      }
    });
  }

  // Chart 7: Donut Chart 3 (Orders - 80%)
  ctx = document.getElementById('chartDonut3');
  if (ctx) {
    new Chart(ctx.getContext("2d"), {
      type: 'doughnut',
      data: {
        labels: ['Completed', 'Other'],
        datasets: [{
          label: "Orders",
          backgroundColor: ['#f17e5d', '#f4f3ef'],
          borderWidth: 0,
          data: [80, 20]
        }]
      },
      options: {
        cutout: '90%',
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        elements: {
          center: {
            text: '80%',
            color: '#66615c',
            fontStyle: 'Arial',
            sidePadding: 60
          }
        }
      }
    });
  }

  // Chart 8: Donut Chart 4 (Subscriptions - 11%)
  ctx = document.getElementById('chartDonut4');
  if (ctx) {
    new Chart(ctx.getContext("2d"), {
      type: 'doughnut',
      data: {
        labels: ['Ended', 'Active'],
        datasets: [{
          label: "Subscriptions",
          backgroundColor: ['#66615b', '#f4f3ef'],
          borderWidth: 0,
          data: [11, 89]
        }]
      },
      options: {
        cutout: '90%',
        plugins: {
          legend: { display: false },
          tooltip: { enabled: false }
        },
        elements: {
          center: {
            text: '11%',
            color: '#66615c',
            fontStyle: 'Arial',
            sidePadding: 60
          }
        }
      }
    });
  }
};
