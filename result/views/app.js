var app = angular.module('cloudwars', []);
var socket = io.connect();

var bg1 = document.getElementById('background-stats-1');
var bg2 = document.getElementById('background-stats-2');
var bg3 = document.getElementById('background-stats-3');

app.controller('statsCtrl', function ($scope) {
  $scope.awsVotes = 0;
  $scope.azureVotes = 0;
  $scope.gcVotes = 0;

  var updateScores = function () {
    socket.on('scores', function (json) {
      data = JSON.parse(json);
      var aws = parseInt(data.aws || 0);
      var azure = parseInt(data.azure || 0);
      var gc = parseInt(data.gc || 0);

      var percentages = getPercentages(aws, azure, gc);

      bg1.style.width = percentages.aws + "%";
      bg2.style.width = percentages.azure + "%";
      bg3.style.width = percentages.gc + "%";

      $scope.$apply(function () {
        $scope.awsVotes = aws;
        $scope.azureVotes = azure;
        $scope.gcVotes = gc;
        $scope.total = aws + azure + gc;
      });
    });
  };

  var init = function () {
    document.body.style.opacity = 1;
    updateScores();
  };
  socket.on('message', function (data) {
    init();
  });
});

function getPercentages(aws, azure, gc) {
  const total = aws + azure + gc;
  let result = {};

  if (total === 0) {
    return { aws: 0, azure: 0, gc: 0 };
  }

  result.aws = Math.round((aws / total) * 100);
  result.azure = Math.round((azure / total) * 100);
  result.gc = Math.round((gc / total) * 100);

  // Ensure non-zero votes are at least 1%
  if (aws > 0 && result.aws === 0) result.aws = 1;
  if (azure > 0 && result.azure === 0) result.azure = 1;
  if (gc > 0 && result.gc === 0) result.gc = 1;

  // Adjust to ensure total is 100%
  const currentTotal = result.aws + result.azure + result.gc;
  const diff = 100 - currentTotal;

  if (diff !== 0) {
    const maxKey = Object.keys(result).reduce((a, b) => result[a] > result[b] ? a : b);
    result[maxKey] += diff;
  }

  return result;
}
